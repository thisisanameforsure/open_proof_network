"""``POST /stewards``: become a problem's steward, or step down, from the site (F23-R8; D-32 v3.33,
D-22 v3.33, D-23, D-35 v3.33).

The service writes the ``steward/v2`` record as the signed-in GitHub login — the login, the fixed
sentence and the date are the service's; the display name and the optional identity link are the
form's — signs it with the network's approval key (``OPN_API_APPROVAL_SIGNING_KEY``, C8) over the
canonical body the gate verifies (``opn_gate.signed.body``), and opens its pull request with the
identity as author (D-23). The record says the service saw that login sign in and ask; it does
not say the steward holds a key (D-32 v3.33).

Admission follows the graph's ``policy.json`` at the current commit: ``open`` (an absent file, or
``policy/v1``, means open) writes ``admitted_by: self`` on an ``append/`` branch the merge actor
merges; ``reviewed`` writes a ``curate/`` branch, which only a curator merges.

The approval key is read here and in ``approvals`` and nowhere else; without it both routes
answer ``503 approval-key-missing`` and nothing is signed with anything else (C7).
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import appends, pending, ratelimit, session, sshsig, submissions
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_gate import policy as policymod
from opn_gate import signed, steward
from opn_gate.signer import NAMESPACE

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

SCHEMA = "steward/v2"
VIA = "approval-key"
SELF = "self"
OPEN = "open"
REVIEWED = "reviewed"
#: F23-R8: a steward record under reviewed admission waits for a curator on this branch prefix.
CURATE_BRANCH_PREFIX = "curate/"
#: F05-T8: what the form sends.
FIELDS: tuple[str, ...] = ("target", "action", "name", "link", "accept")
NAME_MAX = 200  # steward/v2's cap
LINK_MAX = 500  # steward/v2's cap
RECORD_RE = re.compile(r"^(?P<n>[1-9][0-9]*)\.ya?ml$")


# --- shared with ``approvals`` -------------------------------------------------------------------


def github_login(held: Identity) -> str:
    """The login a role is held by. An identity made from the tutorial (D-19) has none, and a
    steward record or an approval names a GitHub login (D-22 v3.33)."""
    login = session.login_of(held)
    if login is None:
        raise ApiError(
            403,
            "github-login-required",
            "only an identity proved with GitHub can steward a problem or approve words; sign in "
            "with GitHub",
        )
    return login


def approval_key(ctx: Context) -> tuple[str, str]:
    """(private key text, public key line) of the approval key, or the 503 that says it is not
    configured (C7). A key that is set but unusable is the same refusal, never a fallback."""
    private = ctx.settings.approval_signing_key
    if not private:
        raise ApiError(
            503,
            "approval-key-missing",
            "the service has no approval key (OPN_API_APPROVAL_SIGNING_KEY); nothing can be "
            "signed through the site until the operator sets it",
        )
    try:
        return private, sshsig.public_key_of(private)
    except sshsig.SshsigError as exc:
        raise ApiError(
            503, "approval-key-missing", f"the configured approval key is unusable: {exc}"
        ) from exc


def sign_record(doc: dict[str, Any], private: str, public: str) -> dict[str, Any]:
    """``doc`` with ``key`` (the approval key's public half) and ``signature`` over the canonical
    body, the bytes ``opn_gate.signed.verifies`` checks (``via: approval-key``)."""
    out = {k: v for k, v in doc.items() if k != signed.SIGNATURE_FIELD}
    out[signed.KEY_FIELD] = public
    out[signed.SIGNATURE_FIELD] = sshsig.sign(signed.body(out), private, namespace=NAMESPACE)
    return out


def bad(message: str, **details: Any) -> ApiError:
    return ApiError(400, "arguments-invalid", message, details=details or None)


# --- the policy ----------------------------------------------------------------------------------


def admission(ctx: Context) -> str:
    """``policy.json``'s ``steward_admission`` at the current commit: an absent file or a
    ``policy/v1`` file is ``open`` (policy/v2). Any other shape is an outage, never a default."""
    body = pending.optional_committed(ctx, policymod.FILE)
    if body is None:
        return OPEN
    try:
        doc = json.loads(body)
    except ValueError as exc:
        raise ApiError(503, "graph-unreadable", f"{policymod.FILE} is not JSON") from exc
    if isinstance(doc, dict) and doc.get("schema") == "policy/v1":
        return OPEN
    value = doc.get("steward_admission") if isinstance(doc, dict) else None
    if value not in (OPEN, REVIEWED):
        raise ApiError(503, "graph-unreadable", f"{policymod.FILE} names no steward_admission")
    return str(value)


def admitted_by(ctx: Context, mode: str) -> str:
    """F23-Q (proposed): ``self`` under open. Under reviewed the record names the curator who
    will merge it, and the signature covers that name, so the service names the first curator
    ``curators.json`` lists (the owner, at Stage 0); a different curator merging it is the
    gate's to refuse."""
    if mode == OPEN:
        return SELF
    curators = session.curator_logins(ctx)
    if not curators:
        raise ApiError(
            409,
            "no-curator",
            "steward admission is reviewed and curators.json lists no curator to review it",
        )
    return curators[0]


# --- the form ------------------------------------------------------------------------------------


def checked(fields: dict[str, Any]) -> tuple[str, str, str, str | None]:
    """(target, action, name, link), or ``400 arguments-invalid`` naming the field."""
    target = fields.get("target")
    if not isinstance(target, str) or not target:
        raise bad("target is required: a target id", field="target")
    action = fields.get("action")
    if action not in (steward.COMMIT, steward.STEP_DOWN):
        raise bad(f"action is {steward.COMMIT!r} or {steward.STEP_DOWN!r}", field="action")
    if fields.get("accept") is not True:
        raise bad(
            "accept must be true: the record states the fixed sentence for its action, verbatim",
            field="accept",
        )
    name = fields.get("name")
    if not isinstance(name, str) or not name.strip() or len(name) > NAME_MAX:
        raise bad(f"name is the display name, 1 to {NAME_MAX} characters", field="name")
    link = fields.get("link")
    if link is not None and (
        not isinstance(link, str) or not link.startswith("https://") or len(link) > LINK_MAX
    ):
        raise bad(f"link is null or an https:// URL of at most {LINK_MAX} characters", field="link")
    return target, str(action), name, link


def next_number(ctx: Context, target_id: str) -> int:
    """``stewards/<n>.yaml`` for the next free ``n``: append-only, never a rewrite."""
    names = session.listing(ctx, f"targets/{target_id}/{steward.DIR}")
    taken = [int(m.group("n")) for n in names if (m := RECORD_RE.match(n)) is not None]
    return max(taken, default=0) + 1


# --- POST /stewards ------------------------------------------------------------------------------


async def post_stewards(ctx: Context, request: Request) -> Response:
    """R8: the record, signed with the approval key, in its own pull request."""
    held: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, FIELDS)
    login = github_login(held)
    target_id, action, name, link = checked(fields)
    private, public = approval_key(ctx)
    appends.known_target(ctx, target_id)
    ratelimit.enforce(
        ctx,
        "steward",
        login.casefold(),
        limit=ctx.settings.stewards_per_day,
        seconds=ratelimit.DAY_S,
    )
    active = session.is_steward(ctx, target_id, login)
    if action == steward.COMMIT and active:
        raise ApiError(
            409, "steward-already-active", f"{login} is already an active steward of {target_id}"
        )
    if action == steward.STEP_DOWN and not active:
        raise ApiError(
            409, "steward-not-active", f"{login} is not an active steward of {target_id}"
        )
    mode = admission(ctx)
    doc = sign_record(
        {
            "schema": SCHEMA,
            "target": target_id,
            "action": action,
            "login": login,
            "name": name,
            "link": link,
            "commitment": steward.SENTENCE_FOR[action],
            "date": ctx.clock.now().strftime("%Y-%m-%d"),
            "via": VIA,
            "admitted_by": admitted_by(ctx, mode),
        },
        private,
        public,
    )
    appends.validated(doc, SCHEMA)
    path = f"targets/{target_id}/{steward.DIR}/{next_number(ctx, target_id)}{steward.SUFFIX}"
    content = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
    prefix = CURATE_BRANCH_PREFIX if mode == REVIEWED else submissions.APPEND_BRANCH_PREFIX
    body = appends.append_pr(
        ctx,
        held,
        path=path,
        content=content,
        subject=f"steward {action}: {login} on {target_id}",
        what="steward record",
        kind="steward",
        target_id=target_id,
        node_id=None,
        written=f"{target_id} {action} {login}",
        branch_prefix=prefix,
    )
    return JSONResponse(receipt(body, prefix), status_code=201)


def receipt(body: dict[str, Any], prefix: str) -> dict[str, Any]:
    """F23's answer: the pull request, its branch and the file it adds."""
    return {
        "pr_number": body["pr_number"],
        "pr_url": body["pr_url"],
        "branch": prefix + str(body["id"]),
        "path": body["path"],
    }
