"""The web session's own routes and the roles it carries (F23-R4; D-22, D-32, D-35 v3.33).

``GET /session`` answers who is signed in on the site and what they may do there: the GitHub
login, whether it is a curator (``curators.json``), and the targets on which it is an active
steward (``targets/*/stewards/*.yaml``), all read from the graph at the service's current commit
through the committed-file cache. ``POST /session/end`` ends the session and clears the cookie.

The roles here decide which controls the site draws and which routes the service lets a login
use (``POST /approvals``); they are not a verdict. A steward record's signature is the gate's to
check, at the merge that admitted it (F23-R9), so this reader counts every record that parses and
names the fixed sentence, and the latest record per login decides: a commit makes the login
active, a step-down ends it, whatever the versions (v1 or v2) of either.
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import auth, frontier, pending
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_api.mcp import reads
from opn_api.mcp.calls import ToolError
from opn_gate import modes, steward

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

log = logging.getLogger(__name__)

#: The steward record versions this reader accepts (F15-R1, F23-R8).
STEWARD_SCHEMAS: frozenset[str] = frozenset({"steward/v1", "steward/v2"})
RECORD_RE = re.compile(r"^(?P<n>[1-9][0-9]*)\.ya?ml$")


# --- roles, read from the graph ------------------------------------------------------------------


def login_of(held: Identity) -> str | None:
    """The GitHub login an identity proved, or ``None`` for one made from the tutorial (D-19):
    only a GitHub login can hold a role (D-22 v3.33)."""
    return held.proof_reference if held.proof_kind == identitymod.PROOF_GITHUB else None


def curator_logins(ctx: Context) -> list[str]:
    """``curators.json``'s ``identities[].github_login``, in file order; none when the graph has
    no file. A file that is not the shape F08-R8 fixes is an outage, never "no curators" (C7)."""
    body = pending.optional_committed(ctx, modes.CURATORS_FILE)
    if body is None:
        return []
    try:
        doc = json.loads(body)
        entries = doc["identities"]
        return [str(e["github_login"]) for e in entries if e.get("github_login")]
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ApiError(
            503, "graph-unreadable", f"{modes.CURATORS_FILE} is not the shape F08-R8 fixes"
        ) from exc


def target_ids(ctx: Context) -> list[str]:
    index = json.loads(frontier.committed(ctx, "targets/index.json"))
    return [str(t["target_id"]) for t in index.get("targets", [])]


def listing(ctx: Context, directory: str) -> list[str]:
    """The names under ``directory`` at the current commit, through the MCP adapter's per-head
    listing cache (F07-T68), so a page view costs the host one listing per target per head."""
    try:
        return reads.listing(ctx, directory)
    except ToolError as exc:
        raise ApiError(
            503, str(exc.doc.get("error", "graph-unreachable")), str(exc.doc.get("message", ""))
        ) from exc


def steward_records(ctx: Context, target_id: str) -> list[tuple[int, dict[str, Any]]]:
    """Every readable steward record of ``target_id`` as ``(n, document)``, in record order. A
    record of an unknown version or an unreadable one is skipped with a warning: the gate refused
    it at the merge, or it is not a record."""
    directory = f"targets/{target_id}/{steward.DIR}"
    out: list[tuple[int, dict[str, Any]]] = []
    for name in listing(ctx, directory):
        m = RECORD_RE.match(name)
        if m is None:
            continue
        body = pending.optional_committed(ctx, f"{directory}/{name}")
        try:
            doc = yaml.safe_load(body or b"")
        except yaml.YAMLError:
            doc = None
        if not isinstance(doc, dict) or doc.get("schema") not in STEWARD_SCHEMAS:
            log.warning("%s/%s is not a steward record this service reads", directory, name)
            continue
        out.append((int(m.group("n")), doc))
    out.sort(key=lambda pair: pair[0])
    return out


def active_stewards(records: list[tuple[int, dict[str, Any]]]) -> list[str]:
    """The logins whose latest record is a commit naming the fixed sentence, in the order they
    became active. Signatures are not checked here: that is the gate's, at the merge (R9)."""
    current: dict[str, None] = {}
    for _, doc in records:
        login = str(doc.get("login", ""))
        action = doc.get("action")
        if doc.get("commitment") != steward.SENTENCE_FOR.get(str(action)):
            continue
        if action == steward.COMMIT:
            current.setdefault(login, None)
        elif action == steward.STEP_DOWN:
            current.pop(login, None)
    return list(current)


def is_steward(ctx: Context, target_id: str, login: str) -> bool:
    return login in active_stewards(steward_records(ctx, target_id))


def stewarded(ctx: Context, login: str) -> list[str]:
    """The targets on which ``login`` is an active steward, in index order."""
    return [t for t in target_ids(ctx) if is_steward(ctx, t, login)]


def is_curator(ctx: Context, login: str) -> bool:
    return login.casefold() in {c.casefold() for c in curator_logins(ctx)}


# --- the routes ----------------------------------------------------------------------------------


SIGNED_OUT: dict[str, Any] = {"signed_in": False}


async def get_session(ctx: Context, request: Request) -> Response:
    """R4: who is signed in, and their roles; ``{"signed_in": false}`` with no live session. Only
    the cookie is read here (a bearer client knows who it is)."""
    found = auth.web_session(ctx, request)
    if found is None:
        return JSONResponse(SIGNED_OUT, headers={"cache-control": "no-store"})
    record, held = found
    login = login_of(held)
    doc = {
        "signed_in": True,
        "login": login,
        "pseudonym": held.pseudonym,
        "curator": bool(login) and is_curator(ctx, login or ""),
        "stewards": stewarded(ctx, login) if login else [],
        "expires": record.get("expires"),
    }
    return JSONResponse(doc, headers={"cache-control": "no-store"})


async def post_session_end(ctx: Context, request: Request) -> Response:
    """R4: the session is dropped from the store and the cookie cleared; 204 whether or not one
    was live, so signing out twice is not an error. The body carries nothing (F05-T8)."""
    await identitymod.body_fields(request, ())
    if auth.web_request(ctx, request):
        auth.end_session(ctx, request)
    response = Response(status_code=204)
    response.headers["set-cookie"] = auth.session_cookie("", 0)
    return response
