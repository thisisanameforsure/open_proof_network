"""``POST /registrations``: record a target's submission to, or registration in, Palomar (F25-R5,
R15; D-3, D-10, D-35 v3.37).

A signed-in curator or an active steward of the target — the F23 web session, or a bearer whose
identity is a GitHub login — records what the registry answered: the registry id and version once
it has issued them, the wrapper repository and commit, the graph commit the wrapper was exported
from, the proof's node and the attestation of its merge, the status, the url and the hashes the
registry recorded. The service writes the ``registration/v1`` record as that login
(``submitted_by`` is the sign-in, never a field of the body), names it
``targets/<id>/registrations/<date>-<n>.yaml`` and opens it on an ``append/`` branch, which the
graph's merge actor takes as it is (its ``SERVICE_PREFIXES`` are ``propose/``, ``append/``,
``submit/``).

It refuses by name what the gate would refuse (``modes.check_registration``) before anything
opens: the login's role (``not-steward-or-curator``), a node that is not the target's
(``registration-proof-unknown``), an attestation the graph lacks
(``registration-attestation-unknown``) or that is not the node's passing one
(``registration-attestation-mismatch``), and a record that fails its schema (``record-invalid``).
Nothing here talks to the registry: the submission is the curator's act outside the network, and
an agent never registers (F25 §7).
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import appends, pending, ratelimit, session, stewards, submissions
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_gate import paths as gatepaths
from opn_gate import registrations

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

SCHEMA = registrations.SCHEMA
KIND = "registration"
#: F05-T8: what ``POST /registrations`` reads; any other top-level key is refused.
FIELDS: tuple[str, ...] = (
    "target_id",
    "registry",
    "registry_id",
    "version",
    "wrapper",
    "graph_commit",
    "proof",
    "status",
    "url",
    "challenge_sha256",
    "solution_sha256",
    "note",
)
#: The fields a record may leave out; each is null when it does (the schema requires the key).
OPTIONAL: tuple[str, ...] = (
    "registry_id",
    "version",
    "url",
    "challenge_sha256",
    "solution_sha256",
    "note",
)
WRAPPER_FIELDS: frozenset[str] = frozenset({"repository", "commit"})
PROOF_FIELDS: frozenset[str] = frozenset({"node", "attestation"})
RECORD_RE = re.compile(r"^(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})-(?P<n>[1-9][0-9]*)\.ya?ml$")


def bad(message: str, field: str) -> ApiError:
    return ApiError(400, "arguments-invalid", message, details={"field": field})


def may_register(ctx: Context, target_id: str, login: str) -> None:
    """D-10 v3.37: a listed curator or an active steward of the target; anyone else is 403, and
    nothing opens."""
    if session.is_curator(ctx, login) or session.is_steward(ctx, target_id, login):
        return
    raise ApiError(
        403,
        "not-steward-or-curator",
        f"{login} is neither an active steward of {target_id} nor a listed curator; only they "
        "may record a registration (D-10 v3.37)",
    )


def checked_object(raw: Any, field: str, keys: frozenset[str]) -> dict[str, Any]:
    """An object with exactly ``keys``, each a string; the values' grammar is the schema's."""
    if not isinstance(raw, dict) or set(raw) != keys:
        raise bad(f"{field} is an object with {', '.join(sorted(keys))}", field)
    for key, value in raw.items():
        if not isinstance(value, str) or not value:
            raise bad(f"{field}.{key} is a non-empty string", f"{field}.{key}")
    return dict(raw)


def record_body(fields: dict[str, Any]) -> dict[str, Any]:
    """The fields the caller chose, shaped: the required ones present and the optional ones null
    when left out. Everything else — enums, patterns, the hashes' grammar — is the schema's, which
    ``appends.validated`` applies with the whole record."""
    out: dict[str, Any] = {}
    for name in ("registry", "graph_commit", "status"):
        value = fields.get(name)
        if not isinstance(value, str) or not value:
            raise bad(f"{name} is required: a string", name)
        out[name] = value
    out["wrapper"] = checked_object(fields.get("wrapper"), "wrapper", WRAPPER_FIELDS)
    out["proof"] = checked_object(fields.get("proof"), "proof", PROOF_FIELDS)
    for name in OPTIONAL:
        out[name] = fields.get(name)
    return out


def checked_proof(ctx: Context, target_id: str, proof: dict[str, str]) -> None:
    """What the gate asks of ``proof`` (``modes.check_registration``), asked of the committed
    graph before anything opens: the node is the target's, and the attestation is on the graph and
    is that node's passing one."""
    node = proof["node"]
    try:
        _, found = appends.node_target(ctx, {"node_id": node})
    except ApiError as exc:
        if exc.code != "node-unknown":
            raise
        found = None
    if found != target_id:
        raise ApiError(
            404,
            "registration-proof-unknown",
            f"{node} is not a node of {target_id}; proof.node names the node whose merged proof "
            "was exported",
            details={"node": node, "target_id": target_id},
        )
    number = proof["attestation"]
    if not re.match(r"^[0-9]{6}$", number):
        raise bad(
            "proof.attestation is the attestation file's six-digit number", "proof.attestation"
        )
    path = pending.attestation_path(int(number))
    raw = pending.optional_committed(ctx, path)
    if raw is None:
        raise ApiError(
            404,
            "registration-attestation-unknown",
            f"the graph has no {path}; name the attestation of the merge that proved {node}",
            details={"path": path},
        )
    try:
        att = json.loads(raw)
    except ValueError:
        att = None
    if not isinstance(att, dict) or att.get("node_id") != node or att.get("verdict") != "pass":
        raise ApiError(
            400,
            "registration-attestation-mismatch",
            f"{path} is not a passing attestation of {node}: it attests "
            f"{att.get('node_id') if isinstance(att, dict) else None!r} with verdict "
            f"{att.get('verdict') if isinstance(att, dict) else None!r}",
            details={"path": path, "node": node},
        )


def next_name(ctx: Context, target_id: str, day: str) -> str:
    """``<day>-<n>.yaml`` for the next free ``n`` of that day: after every record merged under the
    target and every one of this kind still open for it (a pull request the service opened today
    and has not seen merge), so two filed on one day never share a path."""
    directory = f"targets/{target_id}/{gatepaths.REGISTRATIONS_DIR}"
    taken = [
        int(m.group("n"))
        for name in session.listing(ctx, directory)
        if (m := RECORD_RE.match(name)) is not None and m.group("date") == day
    ]
    open_today = sum(
        1
        for found in ctx.store.list_open_submissions()
        if found.kind == KIND and found.target_id == target_id and found.created[:10] == day
    )
    return f"{day}-{max(taken, default=0) + open_today + 1}.yaml"


def render(doc: dict[str, Any]) -> str:
    """The file as it lands: the schema's field order, so a reader meets the registry first."""
    return str(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))


async def post_registrations(ctx: Context, request: Request) -> Response:
    """R15: one registration record, as the sign-in, in its own pull request."""
    held: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, FIELDS)
    login = stewards.github_login(held)
    target_id = appends.known_target(ctx, fields.get("target_id"))
    chosen = record_body(fields)
    ratelimit.enforce(
        ctx,
        KIND,
        login.casefold(),
        limit=ctx.settings.stewards_per_day,
        seconds=ratelimit.DAY_S,
    )
    may_register(ctx, target_id, login)
    day = ctx.clock.now().strftime("%Y-%m-%d")
    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "target": target_id,
        "registry": chosen["registry"],
        "registry_id": chosen["registry_id"],
        "version": chosen["version"],
        "wrapper": chosen["wrapper"],
        "graph_commit": chosen["graph_commit"],
        "proof": chosen["proof"],
        "status": chosen["status"],
        "submitted_by": login,
        "date": day,
        "url": chosen["url"],
        "challenge_sha256": chosen["challenge_sha256"],
        "solution_sha256": chosen["solution_sha256"],
        "note": chosen["note"],
    }
    appends.validated(doc, SCHEMA)
    checked_proof(ctx, target_id, chosen["proof"])
    path = f"targets/{target_id}/{gatepaths.REGISTRATIONS_DIR}/{next_name(ctx, target_id, day)}"
    body = appends.append_pr(
        ctx,
        held,
        path=path,
        content=render(doc),
        subject=f"registration: {target_id} {chosen['status']} by {login}",
        what="registration record",
        kind=KIND,
        target_id=target_id,
        node_id=None,
        written=appends.written_record(doc),
    )
    return JSONResponse(stewards.receipt(body, submissions.APPEND_BRANCH_PREFIX), status_code=201)
