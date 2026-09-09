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
import hashlib
import html
import json
import os
import re
import secrets
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from opn_api import auth, ratelimit
from opn_api import clock as clockmod
from opn_api import githost as githostmod
from opn_api.app import ApiError
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


async def body_fields(request: Request) -> tuple[dict[str, Any], bool]:
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
    if (
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
    if wants_json(request):
        return JSONResponse(
            {
                "proof": proof,
                "login": user.login,
                "dco": {"version": DCO_VERSION},
                "expires_in_s": ctx.settings.state_ttl_s,
                "next": "POST /tokens {proof, pseudonym, dco: {version, accepted: true}}",
            }
        )
    return HTMLResponse(token_form(login=user.login, proof_id=proof_id))


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


async def post_tokens(ctx: Context, request: Request) -> Response:
    """R4: proof + pseudonym + DCO -> identity and one token, shown once.

    Two proof kinds, one issuance path: ``github`` (F05-R4) and ``tutorial`` (F06-R7).
    """
    fields, was_form = await body_fields(request)
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
    if kind == PROOF_TUTORIAL:
        reference, undo = tutorial_reference(ctx, request, proof)
    else:
        reference, undo = github_reference(ctx, proof)
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
    token = auth.new_token()
    ctx.store.put_token(
        TokenRecord(
            token_hash=auth.token_hash(ctx.settings.token_secret or "", token),
            identity_id=identity.id,
            created=identity.created,
        )
    )
    doc = {
        "token": token,
        "identity": {
            "id": identity.id,
            "pseudonym": identity.pseudonym,
            "proof_kind": identity.proof_kind,
            "created": identity.created,
        },
    }
    if was_form and not wants_json(request):
        return HTMLResponse(token_page(doc), status_code=201)
    return JSONResponse(doc, status_code=201)


# --- the two pages (escaped; no script, no off-origin reference) ---------------------------------

_STYLE = (
    "body{font:16px/1.5 system-ui,sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem}"
    "pre{white-space:pre-wrap;background:#f4f4f4;padding:1rem;font-size:.85em}"
    "code{background:#f4f4f4;padding:.1em .3em}label{display:block;margin:1rem 0}"
)


def token_form(*, login: str, proof_id: str) -> str:
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
        "<label>Pseudonym <input name='pseudonym' required pattern='[A-Za-z0-9-]{1,39}'></label>"
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
        f"created {html.escape(str(identity['created']))}.</p>"
    )
