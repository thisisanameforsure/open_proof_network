"""Claims (F05-R7, R8; D-25; Q1): advisory, non-exclusive, with a TTL inside published caps.

``POST /claims`` checks the node against the committed frontier at ``main`` (present and
claimable), clamps an undeclared TTL to the minimum, rejects one above the maximum, enforces
the active-claim cap, and returns the receipt. ``DELETE /claims/<id>`` releases the holder's
own claim. Expiry is lazy: a claim past ``expires`` counts as released wherever it is read.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import clock as clockmod
from opn_api import frontier, ratelimit
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_api.store import Claim, Identity, release

if TYPE_CHECKING:
    from opn_api.app import Context

NODE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def receipt(claim: Claim, pseudonym: str) -> dict[str, Any]:
    return {
        "id": claim.id,
        "node_id": claim.node_id,
        "target_id": claim.target_id,
        "pseudonym": pseudonym,
        "created": claim.created,
        "expires": claim.expires,
        "released": claim.released,
    }


def ttl_hours(ctx: Context, raw: Any) -> int:
    """R7: undeclared -> minimum; above the maximum -> 400; below the minimum -> the minimum."""
    lo, hi = ctx.settings.claim_ttl_min_h, ctx.settings.claim_ttl_max_h
    if raw is None:
        return lo
    if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        raise ApiError(400, "ttl-invalid", "ttl_hours must be a positive integer")
    if raw > hi:
        raise ApiError(400, "ttl-above-cap", f"ttl_hours {raw} exceeds the published cap of {hi}")
    return max(raw, lo)


def find_entry(ctx: Context, node_id: str, target_id: str | None) -> dict[str, Any]:
    entries = [
        e
        for e in frontier.committed_frontier(ctx)["entries"]
        if e["node_id"] == node_id and (target_id is None or e["target_id"] == target_id)
    ]
    if not entries:
        raise ApiError(404, "node-not-in-frontier", f"{node_id} is not in the frontier at main")
    if len(entries) > 1:
        raise ApiError(
            409, "node-ambiguous", f"{node_id} exists in several targets; pass target_id"
        )
    entry: dict[str, Any] = entries[0]
    if not entry.get("claimable"):
        raise ApiError(409, "node-not-claimable", f"{node_id} is not claimable")
    return entry


def active_for(ctx: Context, identity_id: str) -> list[Claim]:
    now = clockmod.render(ctx.clock.now())
    return [
        c
        for c in ctx.store.list_claims()
        if c.identity_id == identity_id and frontier.is_active(c, now)
    ]


async def post_claims(ctx: Context, request: Request) -> Response:
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request)
    node_id = fields.get("node_id")
    if not isinstance(node_id, str) or not NODE_ID_RE.match(node_id):
        raise ApiError(400, "node-id-invalid", "node_id must match ^[a-z0-9][a-z0-9-]*$")
    target_id = fields.get("target_id")
    bad_target = not isinstance(target_id, str) or not NODE_ID_RE.match(target_id)
    if target_id is not None and bad_target:
        raise ApiError(400, "target-id-invalid", "target_id must match ^[a-z0-9][a-z0-9-]*$")
    hours = ttl_hours(ctx, fields.get("ttl_hours"))
    entry = find_entry(ctx, node_id, target_id)
    now = ctx.clock.now()
    held = active_for(ctx, identity.id)
    if len(held) >= ctx.settings.active_claims:
        soonest = min(c.expires for c in held)
        raise ApiError(
            429,
            "active-claims-cap",
            f"{ctx.settings.active_claims} active claims already; release one or wait",
            headers={"Retry-After": ratelimit.retry_after(now, clockmod.parse(soonest))},
        )
    claim = Claim(
        id=identitymod.new_ulid(now),
        node_id=node_id,
        target_id=str(entry["target_id"]),
        identity_id=identity.id,
        created=clockmod.render(now),
        expires=clockmod.render(now + timedelta(hours=hours)),
    )
    ctx.store.put_claim(claim)
    return JSONResponse(receipt(claim, identity.pseudonym), status_code=201)


async def delete_claim(ctx: Context, request: Request) -> Response:
    identity: Identity = request.state.identity
    claim = ctx.store.get_claim(str(request.path_params["claim_id"]))
    if claim is None:
        raise ApiError(404, "claim-unknown", "no such claim")
    if claim.identity_id != identity.id:
        raise ApiError(403, "not-holder", "only the claim's holder may release it")
    now = ctx.clock.now()
    if claim.released is None:
        claim = release(claim, now)
        ctx.store.put_claim(claim)
    return JSONResponse(receipt(claim, identity.pseudonym))
