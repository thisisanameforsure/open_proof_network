"""The claim overlay (F05-R9; D-25, D-35): ``GET /frontier.json`` and ``GET /claims.json``.

``committed`` fetches a file at the graph's ``main`` through the ``GitHost`` seam, reusing it
for ``frontier_max_stale_s`` seconds and revalidating by ETag after that; a fetch failure
serves the last good copy with a warning, or 503 when there is none (C7). ``registry`` turns
the claims table into the per-node ``{active, history_count}`` shape, treating a claim past
its expiry as released on every read (R8: no background job).
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import clock as clockmod
from opn_api.app import ApiError, CachedFile
from opn_api.githost import GitHostError
from opn_api.store import Claim
from opn_gate import schemas

if TYPE_CHECKING:
    from opn_api.app import Context

log = logging.getLogger(__name__)

FRONTIER_PATH = "frontier.json"
#: The frontier versions this service will serve. A product names its own version and
#: several are live at once (D-34, F11-R4), so what is pinned is the set: a graph that
#: published something outside it is refused rather than passed through unvalidated.
FRONTIER_SCHEMAS: tuple[str, ...] = ("frontier/v1", "frontier/v2")
CLAIMS_SCHEMA = "claims/v1"
EMPTY_CLAIMS: dict[str, Any] = {"active": [], "history_count": 0}


def committed(ctx: Context, path: str) -> bytes:
    cached = ctx.files.setdefault(path, CachedFile(path))
    now = time.monotonic()
    if cached.body is not None and now - cached.fetched_at < ctx.settings.frontier_max_stale_s:
        return cached.body
    try:
        got = ctx.githost.fetch_raw(
            ctx.settings.graph_repo, ctx.settings.graph_branch, path, etag=cached.etag
        )
    except GitHostError as exc:
        got = None
        log.warning("%s: %s", path, exc)
    if got is not None and got.status == 200 and got.body is not None:
        cached.body, cached.etag, cached.fetched_at = got.body, got.etag, now
    elif got is not None and got.status == 304 and cached.body is not None:
        cached.fetched_at = now
    elif got is not None:
        log.warning("%s: graph returned %d", path, got.status)
    if cached.body is None:
        raise ApiError(503, "graph-unreachable", f"cannot read {path} from the graph")
    return cached.body


def is_active(claim: Claim, now: str) -> bool:
    """Unreleased and not past ``expires`` (string comparison is safe: one fixed format)."""
    return claim.released is None and claim.expires > now


def registry(ctx: Context) -> dict[str, dict[str, Any]]:
    """Per node: ``active`` [{pseudonym, expires}] and ``history_count`` (R9)."""
    now = clockmod.render(ctx.clock.now())
    names: dict[str, str] = {}
    out: dict[str, dict[str, Any]] = {}
    for claim in ctx.store.list_claims():
        entry = out.setdefault(claim.node_id, {"active": [], "history_count": 0})
        entry["history_count"] += 1
        if not is_active(claim, now):
            continue
        if claim.identity_id not in names:
            identity = ctx.store.get_identity(claim.identity_id)
            names[claim.identity_id] = identity.pseudonym if identity else "?"
        entry["active"].append({"pseudonym": names[claim.identity_id], "expires": claim.expires})
    for entry in out.values():
        entry["active"].sort(key=lambda a: (str(a["expires"]), str(a["pseudonym"])))
    return dict(sorted(out.items()))


def overlay(doc: dict[str, Any], reg: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The committed frontier with only the ``claims`` fields replaced (AC15)."""
    out = dict(doc)
    out["entries"] = [
        {**e, "claims": dict(reg.get(str(e["node_id"]), EMPTY_CLAIMS))} for e in doc["entries"]
    ]
    return out


def validate_frontier(doc: dict[str, Any]) -> dict[str, Any]:
    """Validate against the version the document declares, constrained to the set above."""
    declared = str(doc.get("schema"))
    if declared not in FRONTIER_SCHEMAS:
        msg = (
            f"frontier.json declares {declared!r}; this service serves "
            f"{', '.join(FRONTIER_SCHEMAS)}"
        )
        raise schemas.SchemaError(msg)
    return schemas.validate(doc, declared)


def committed_frontier(ctx: Context) -> dict[str, Any]:
    doc: dict[str, Any] = json.loads(committed(ctx, FRONTIER_PATH))
    return doc


async def get_frontier(ctx: Context, request: Request) -> Response:
    doc = overlay(committed_frontier(ctx), registry(ctx))
    return JSONResponse(validate_frontier(doc))


def snapshot(ctx: Context) -> dict[str, Any]:
    """``claims.json``: the registry alone, the shape the post-merge job commits (R10, Q3)."""
    return {
        "schema": CLAIMS_SCHEMA,
        "snapshot_at": clockmod.render(ctx.clock.now()),
        "nodes": registry(ctx),
    }


async def get_claims(ctx: Context, request: Request) -> Response:
    return JSONResponse(schemas.validate(snapshot(ctx), CLAIMS_SCHEMA))
