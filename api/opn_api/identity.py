"""Identity and token issuance (F05-R3, R4, R6; F06-R7; D-19, D-23; Q4).

The GitHub proof is a browser flow: ``GET /auth/github/start`` sends the browser to GitHub
with a single-use state nonce; the callback exchanges the code through the ``GitHost`` seam
(the access token dies inside it), keeps a short-lived *proof* {login, id, created_at} in the
store, and shows a form. ``POST /tokens`` takes the proof id, a pseudonym and the DCO
acceptance, creates the identity and returns the token once. A JSON client can drive the same
three steps: the callback answers JSON when asked for it.

D-19's second proof needs no account at all: prove the tutorial node and the passing precheck
job *is* the credential. ``POST /tokens`` accepts proof kind ``tutorial`` {job_id, nonce} for
a job that was created without a token and passed, consuming the nonce (F06-R7). The job id
is the identity's proof reference, so the store's uniqueness rule makes one job worth one
identity, exactly as one GitHub login is worth one.
"""

from __future__ import annotations

import dataclasses
import functools
import hashlib
import html
import json
import os
import re
import secrets
from collections.abc import Callable, Collection, Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from opn_api import auth, ratelimit
from opn_api import clock as clockmod
from opn_api import githost as githostmod
from opn_api.app import ApiError
from opn_api.config import Settings
from opn_api.githost import GitHostError
from opn_api.store import KEY_PROOF, KEY_STATE, ConflictError, Identity, TokenRecord

if TYPE_CHECKING:
    from opn_api.app import Context

PROOF_GITHUB = "github"
PROOF_TUTORIAL = "tutorial"  # D-19, F06-R7: a passing anonymous precheck of the tutorial node
PROOF_KINDS: tuple[str, ...] = (PROOF_GITHUB, PROOF_TUTORIAL)
PSEUDONYM_RE = re.compile(r"^[A-Za-z0-9-]{1,39}$")
CALLBACK_PATH = "/auth/github/callback"

DCO_TEXT = """Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.


Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
"""
DCO_VERSION = hashlib.sha256(DCO_TEXT.encode("utf-8")).hexdigest()[:16]

# --- ids ---------------------------------------------------------------------------------------

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid(now: datetime) -> str:
    """A ULID (§6): 48-bit millisecond time then 80 random bits, Crockford base32."""
    ms = int(now.timestamp() * 1000)
    value = (ms << 80) | int.from_bytes(os.urandom(10), "big")
    out = []
    for _ in range(26):
        out.append(_CROCKFORD[value & 31])
        value >>= 5
    return "".join(reversed(out))


# --- request bodies ------------------------------------------------------------------------------


async def _parse_body(request: Request) -> tuple[dict[str, Any], bool]:
    """(fields, was_form): JSON, or a urlencoded form (parsed here; no multipart package, C5)."""
    raw = await request.body()
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type == "application/x-www-form-urlencoded":
        parsed = parse_qs(raw.decode("utf-8", "replace"), keep_blank_values=True)
        flat: dict[str, Any] = {k: v[-1] for k, v in parsed.items()}
        return _nest(flat), True
    if not raw.strip():
        return {}, False
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise ApiError(400, "malformed-body", "the body is not valid JSON") from exc
    if not isinstance(doc, dict):
        raise ApiError(400, "malformed-body", "the body must be a JSON object")
    return doc, False


def refuse_unknown(fields: Mapping[str, Any], accepted: Collection[str]) -> None:
    """F05-T8 (finding 5): a top-level key the route does not define is a 400 naming every such
    key and listing the accepted ones, never silently ignored. Only top-level keys: what sits
    inside a field's object is that field's own business (``tooling`` keeps its three names, a
    record is validated by its schema). A form is checked after nesting, so ``proof.id`` counts
    as ``proof``."""
    unknown = sorted(k for k in fields if k not in accepted)
    if unknown:
        allowed = sorted(accepted)
        raise ApiError(
            400,
            "unknown-field",
            f"unknown field{'s' if len(unknown) > 1 else ''} {', '.join(unknown)}; "
            f"this route accepts {', '.join(allowed)}",
            details={"unknown": unknown, "accepted": allowed},
        )


async def body_fields(request: Request, accepted: Collection[str]) -> tuple[dict[str, Any], bool]:
    """(fields, was_form), after refusing any top-level key outside ``accepted`` (F05-T8). The
    allowlist is required, so a body-taking handler cannot forget the rule; it runs before the
    handler reads a field, and so before any token is spent, limit charged or branch pushed."""
    fields, was_form = await _parse_body(request)
    refuse_unknown(fields, accepted)
    return fields, was_form


def _nest(flat: dict[str, Any]) -> dict[str, Any]:
    """``proof.id=x`` -> ``{"proof": {"id": "x"}}``; ``dco.accepted=on`` -> ``True``."""
    out: dict[str, Any] = {}
    for key, value in flat.items():
        head, _, tail = key.partition(".")
        if tail:
            out.setdefault(head, {})[tail] = value
        else:
            out[key] = value
    if isinstance(out.get("dco"), dict):
        accepted = str(out["dco"].get("accepted", "")).lower()
        out["dco"]["accepted"] = accepted in ("on", "true", "1", "yes")
    return out


def wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "application/json" in accept and "text/html" not in accept


# --- DCO ---------------------------------------------------------------------------------------


async def get_dco(ctx: Context, request: Request) -> Response:
    """The DCO text and the version a token request must name (R4)."""
    return JSONResponse({"version": DCO_VERSION, "text": DCO_TEXT})


def check_dco(doc: Any) -> None:
    if not isinstance(doc, dict) or doc.get("accepted") is not True:
        raise ApiError(400, "dco-not-accepted", "the DCO must be accepted (dco.accepted: true)")
    if doc.get("version") != DCO_VERSION:
        raise ApiError(
            400,
            "dco-version-stale",
            f"dco.version must be the current DCO text hash {DCO_VERSION}; read GET /dco.json",
        )


# --- reserved pseudonyms (F05-T26; D-19 v3.28, Q26) ----------------------------------------------

#: The published list of reserved names, one per line: the owner adds a name here (Q26).
RESERVED_FILE = Path(__file__).with_name("reserved_pseudonyms.txt")


def fold(name: str) -> str:
    """How two names are compared: without regard to case, and with ``-`` and ``_`` removed, so
    ``Opn_Gate`` and ``opngate`` are both the gate's own name."""
    return name.lower().replace("-", "").replace("_", "")


@functools.cache
def published_reserved() -> frozenset[str]:
    """The names on ``RESERVED_FILE``, folded; ``#`` starts a comment. Read once per process.
    A missing file is an error, never an empty list: the reservation must not lapse silently
    because the package shipped without its data (C7)."""
    names = set()
    for line in RESERVED_FILE.read_text(encoding="utf-8").splitlines():
        entry = line.split("#", 1)[0].strip()
        if entry:
            names.add(fold(entry))
    return frozenset(names)


def _owner(repo: str) -> str:
    return repo.split("/", 1)[0]


def reserved_names(settings: Settings) -> frozenset[str]:
    """Every reserved name, folded: the operator's logins as configuration knows them (the
    owners of the graph, network and precheck repositories), the App's committer name less its
    ``[bot]`` suffix, and the published list. Nothing about the deployment is written in code."""
    configured = {
        _owner(settings.graph_repo),
        _owner(settings.network_repo),
        _owner(settings.precheck_repo),
        settings.committer_name.removesuffix("[bot]"),
    }
    return frozenset(fold(n) for n in configured if n) | published_reserved()


def is_reserved(settings: Settings, name: str) -> bool:
    return fold(name) in reserved_names(settings)


def check_not_reserved(settings: Settings, pseudonym: str) -> None:
    """F05-T26: a new identity may not take a reserved name (D-19 v3.28). Checked only when an
    identity is created: one that already holds a name reserved later keeps it."""
    if is_reserved(settings, pseudonym):
        raise ApiError(
            409,
            "pseudonym-reserved",
            f"pseudonym {pseudonym!r} is reserved (the operator's, the gate's own, or a name on "
            "the published list, compared without case or separators); choose another",
        )


def check_pseudonym(value: Any) -> str:
    if not isinstance(value, str) or not PSEUDONYM_RE.match(value):
        raise ApiError(
            400, "pseudonym-invalid", "pseudonym: 1-39 characters from [A-Za-z0-9-] (R4)"
        )
    return value


# --- GitHub OAuth --------------------------------------------------------------------------------


def redirect_uri(ctx: Context) -> str:
    return ctx.settings.public_url + CALLBACK_PATH


def expiry(ctx: Context) -> datetime:
    return ctx.clock.now() + timedelta(seconds=ctx.settings.state_ttl_s)


async def github_start(ctx: Context, request: Request) -> Response:
    """R3: a state nonce, then GitHub's authorization page. Per-source limited (R6)."""
    ratelimit.check_token_start(ctx, ratelimit.client_address(request))
    state = secrets.token_urlsafe(24)
    ctx.store.put_ephemeral(
        KEY_STATE + state, {"created": clockmod.render(ctx.clock.now())}, expiry(ctx)
    )
    url = githostmod.authorize_url(
        client_id=ctx.settings.github_client_id or "", redirect_uri=redirect_uri(ctx), state=state
    )
    return RedirectResponse(url, status_code=302)


async def github_callback(ctx: Context, request: Request) -> Response:
    """R3: exchange the code, drop the access token, keep a proof, ask for pseudonym and DCO."""
    code = request.query_params.get("code", "")
    state = request.query_params.get("state", "")
    if not code or not state:
        raise ApiError(400, "callback-incomplete", "GitHub's callback needs code and state")
    if ctx.store.take_ephemeral(KEY_STATE + state, ctx.clock.now()) is None:
        raise ApiError(400, "state-invalid", "unknown, used or expired state; start again")
    try:
        user = ctx.githost.exchange_code(code, redirect_uri=redirect_uri(ctx))
    except GitHostError as exc:
        raise ApiError(502, "github-exchange-failed", str(exc)) from exc
    existing = ctx.store.get_identity_by_proof(PROOF_GITHUB, user.login)
    if existing is not None:
        check_reprovable(ctx, existing, user.login)  # F05-T27: a lapsed identity re-proves
    elif (
        ctx.store.count_identities_by_proof(PROOF_GITHUB, user.login)
        >= ctx.settings.tokens_per_login
    ):
        raise ApiError(
            409, "github-login-taken", f"an identity already exists for GitHub login {user.login}"
        )
    proof_id = secrets.token_urlsafe(24)
    ctx.store.put_ephemeral(
        KEY_PROOF + proof_id,
        {"login": user.login, "github_id": user.id, "created_at": user.created_at},
        expiry(ctx),
    )
    proof = {"kind": PROOF_GITHUB, "id": proof_id}
    held = existing.pseudonym if existing is not None else None
    if wants_json(request):
        doc: dict[str, Any] = {
            "proof": proof,
            "login": user.login,
            "dco": {"version": DCO_VERSION},
            "expires_in_s": ctx.settings.state_ttl_s,
            "next": "POST /tokens {proof, pseudonym, dco: {version, accepted: true}}",
        }
        if held is not None:  # F05-T27: the pseudonym the new token must be asked for under
            doc["pseudonym"] = held
        return JSONResponse(doc)
    return HTMLResponse(token_form(login=user.login, proof_id=proof_id, pseudonym=held))


# --- a lapsed identity re-proves (F05-T27; D-19 v3.28, Q27) --------------------------------------


def reprovable(ctx: Context, held: Identity) -> bool:
    """Whether the proof that made ``held`` may give it a new token: none of its tokens is live
    (a lost live token is replaced by the recovery code, F05-T30, or waits out its idle window),
    and none was revoked by the operator (F05-T21) — a lapse after a revocation must not undo it.
    A token retired by a rotation is neither."""
    for record in ctx.store.list_tokens(held.id):
        if record.revoked and not record.renewed:
            return False
        if not record.revoked and not auth.lapsed(ctx, record):
            return False
    return True


def check_reprovable(ctx: Context, held: Identity, reference: str) -> None:
    if not reprovable(ctx, held):
        raise ApiError(
            409,
            "github-login-taken",
            f"an identity already exists for GitHub login {reference} ({held.pseudonym}); a new "
            "token for it is issued by this proof only once its tokens have lapsed from disuse, "
            "and never after the operator revoked them. A lost live token is replaced with the "
            "identity's recovery code: POST /tokens/recover {pseudonym, recovery_code}",
        )


def issue(ctx: Context, identity_id: str, now: datetime) -> tuple[str, TokenRecord]:
    """A new token for ``identity_id``, issued at ``now``. It has no fixed end: it lapses only
    after ``OPN_API_TOKEN_IDLE_DAYS`` without use (D-19 v3.29, F05-T29)."""
    token = auth.new_token()
    record = TokenRecord(
        token_hash=auth.token_hash(ctx.settings.token_secret or "", token),
        identity_id=identity_id,
        created=clockmod.render(now),
        last_used=clockmod.render(now),  # issue counts as a use: only a legacy token has none
    )
    return token, record


def token_doc(ctx: Context, token: str, held: Identity) -> dict[str, Any]:
    """The answer that shows a token once. ``idle_days``: how long it may go unused before it
    lapses (D-19 v3.29); a token in use never lapses."""
    return {
        "token": token,
        "identity": {
            "id": held.id,
            "pseudonym": held.pseudonym,
            "proof_kind": held.proof_kind,
            "created": held.created,
        },
        "idle_days": ctx.settings.token_idle_days,
    }


# --- the two proofs a token may be minted from ---------------------------------------------------

Undo = Callable[[], None]


def github_reference(ctx: Context, proof: dict[str, Any]) -> tuple[str, Undo]:
    """F05-R4: consume the short-lived proof the callback stored, and answer with the login.

    The proof is taken now so that two concurrent requests cannot both spend it; ``undo`` puts
    it back, which is what lets a pseudonym clash be retried (AC3).
    """
    proof_id = str(proof.get("id", ""))
    record = ctx.store.take_ephemeral(KEY_PROOF + proof_id, ctx.clock.now()) if proof_id else None
    if record is None:
        raise ApiError(400, "proof-invalid", "unknown, used or expired proof; start again")

    def undo() -> None:
        ctx.store.put_ephemeral(KEY_PROOF + proof_id, record, expiry(ctx))

    return str(record["login"]), undo


def tutorial_reference(ctx: Context, request: Request, proof: dict[str, Any]) -> tuple[str, Undo]:
    """F06-R7: a passing anonymous precheck of the tutorial node, spent once.

    Every refusal is the same 400: which condition failed — no such job, still running, failed,
    authenticated, wrong or already-spent nonce — is not something an unauthenticated caller
    gets to probe for. The job id is the proof reference, so the store's uniqueness rule holds
    the "one job, one identity" line even if the nonce check were ever bypassed.
    """
    from opn_api import precheck  # noqa: PLC0415 — precheck imports this module

    ratelimit.check_token_start(ctx, ratelimit.client_address(request))
    refusal = ApiError(400, "proof-invalid", "unknown, unfinished, used or unusable tutorial proof")
    job_id = str(proof.get("job_id", ""))
    nonce = str(proof.get("nonce", ""))
    job = precheck.load(ctx, job_id) if job_id else None
    if job is None or not job.anonymous or not job.nonce or job.nonce_consumed:
        raise refusal
    if not secrets.compare_digest(job.nonce, nonce):
        raise refusal
    job = precheck.advance(ctx, job)  # a job that finished but was never polled still counts
    if job.state != "done" or (job.result or {}).get("verdict") != "pass":
        raise refusal
    precheck.save(ctx, dataclasses.replace(job, nonce_consumed=True))

    def undo() -> None:
        current = precheck.load(ctx, job_id)
        if current is not None:
            precheck.save(ctx, dataclasses.replace(current, nonce_consumed=False))

    return job.id, undo


# --- POST /tokens --------------------------------------------------------------------------------


#: F05-T8: the fields ``POST /tokens`` reads, JSON or form (after ``proof.*`` and ``dco.*`` nest).
TOKEN_FIELDS: tuple[str, ...] = ("proof", "pseudonym", "dco")


async def post_tokens(ctx: Context, request: Request) -> Response:
    """R4: proof + pseudonym + DCO -> identity and one token, shown once.

    Two proof kinds, one issuance path: ``github`` (F05-R4) and ``tutorial`` (F06-R7).
    """
    fields, was_form = await body_fields(request, TOKEN_FIELDS)
    pseudonym = check_pseudonym(fields.get("pseudonym"))
    check_dco(fields.get("dco"))
    proof = fields.get("proof")
    kind = proof.get("kind") if isinstance(proof, dict) else None
    if kind not in PROOF_KINDS:
        raise ApiError(
            400, "proof-unsupported", f"proof.kind must be one of {', '.join(PROOF_KINDS)}"
        )
    assert isinstance(proof, dict)
    now = ctx.clock.now()
    existing: Identity | None = None
    if kind == PROOF_TUTORIAL:
        # A tutorial proof is a job, spent once: it can only ever make a new identity.
        check_not_reserved(ctx.settings, pseudonym)
        reference, undo = tutorial_reference(ctx, request, proof)
    else:
        reference, undo = github_reference(ctx, proof)
        try:
            existing = ctx.store.get_identity_by_proof(PROOF_GITHUB, reference)
            if existing is None:
                check_not_reserved(ctx.settings, pseudonym)
            else:
                # F05-T27 (D-19 v3.28): the same login re-proves a lapsed identity, under its
                # own pseudonym; reservation governs new identities only (F05-T26).
                check_reprovable(ctx, existing, reference)
                if existing.pseudonym.lower() != pseudonym.lower():
                    raise ApiError(
                        409,
                        "github-login-taken",
                        f"GitHub login {reference} already holds the identity "
                        f"{existing.pseudonym!r}; ask for its new token under that pseudonym",
                    )
        except ApiError:
            undo()  # the proof survives, as for a clash (AC3)
            raise
    if existing is not None:
        identity = existing
    else:
        identity = Identity(
            id=new_ulid(now),
            pseudonym=pseudonym,
            proof_kind=str(kind),
            proof_reference=reference,
            created=clockmod.render(now),
        )
        try:
            ctx.store.put_identity(identity)
        except ConflictError as exc:
            # The proof survives a pseudonym clash so the person can pick another (AC3).
            undo()
            if exc.what == "pseudonym":
                raise ApiError(409, "pseudonym-taken", f"pseudonym {pseudonym!r} is taken") from exc
            taken = "github-login-taken" if kind == PROOF_GITHUB else "proof-invalid"
            raise ApiError(409, taken, f"an identity already exists for {reference}") from exc
    token, record = issue(ctx, identity.id, now)
    ctx.store.put_token(record)
    doc = token_doc(ctx, token, identity)
    if was_form and not wants_json(request):
        return HTMLResponse(token_page(doc), status_code=201)
    return JSONResponse(doc, status_code=201)


# --- POST /tokens/renew: optional rotation (F05-T27, T29; D-19 v3.29, Q27, Q29) ----------------


async def post_renew(ctx: Context, request: Request) -> Response:
    """Rotation, optional and never required (D-19 v3.29): a *new* token for the same identity and
    the presented one retired at once. A holder who suspects a copy rotates, and the copy dies;
    if a thief rotates first, the owner's next call is refused with a message saying a renewal
    happened, which is how they learn of the leak. One token rotates once, even when two
    rotations race (``Store.renew_token``). A lapsed token cannot rotate (``token-expired``); its
    identity recovers instead. The body carries nothing."""
    await body_fields(request, ())
    record, held = auth.authenticated(ctx, request)  # the route table already charged the write
    now = ctx.clock.now()
    token, fresh = issue(ctx, held.id, now)
    if not ctx.store.renew_token(record.token_hash, fresh, clockmod.render(now)):
        raise ApiError(
            401,
            "invalid-token",
            "this token was renewed or revoked while the renewal ran",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return JSONResponse(token_doc(ctx, token, held), status_code=201)


# --- the two pages (escaped; no script, no off-origin reference) ---------------------------------

_STYLE = (
    "body{font:16px/1.5 system-ui,sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem}"
    "pre{white-space:pre-wrap;background:#f4f4f4;padding:1rem;font-size:.85em}"
    "code{background:#f4f4f4;padding:.1em .3em}label{display:block;margin:1rem 0}"
)


def token_form(*, login: str, proof_id: str, pseudonym: str | None = None) -> str:
    return (
        "<!doctype html><meta charset='utf-8'><title>Open Proof Network — token</title>"
        f"<style>{_STYLE}</style>"
        f"<h1>Choose a pseudonym</h1><p>GitHub login <code>{html.escape(login)}</code> is proven. "
        "Pick the pseudonym the ledger will show (1-39 characters, letters, digits and hyphens) "
        "and accept the Developer Certificate of Origin.</p>"
        "<form method='post' action='/tokens'>"
        f"<input type='hidden' name='proof.kind' value='{PROOF_GITHUB}'>"
        f"<input type='hidden' name='proof.id' value='{html.escape(proof_id, quote=True)}'>"
        f"<input type='hidden' name='dco.version' value='{DCO_VERSION}'>"
        "<label>Pseudonym <input name='pseudonym' required pattern='[A-Za-z0-9-]{1,39}'"
        + (f" value='{html.escape(pseudonym, quote=True)}'" if pseudonym else "")
        + "></label>"
        f"<pre>{html.escape(DCO_TEXT)}</pre>"
        "<label><input type='checkbox' name='dco.accepted' value='true' required> "
        "I certify the above for every contribution made under this pseudonym.</label>"
        "<button type='submit'>Issue my token</button></form>"
    )


def token_page(doc: dict[str, Any]) -> str:
    identity = doc["identity"]
    return (
        "<!doctype html><meta charset='utf-8'><title>Open Proof Network — token</title>"
        f"<style>{_STYLE}</style>"
        f"<h1>Token for {html.escape(str(identity['pseudonym']))}</h1>"
        "<p>This token is shown once and never again. Give it to your agent as "
        "<code>Authorization: Bearer …</code>.</p>"
        f"<pre>{html.escape(str(doc['token']))}</pre>"
        f"<p>Identity <code>{html.escape(str(identity['id']))}</code>, "
        f"created {html.escape(str(identity['created']))}. A token in use never lapses; one "
        f"left unused for {html.escape(str(doc['idle_days']))} days does.</p>"
    )
