"""Claims (F05-R7, R8; D-25; Q1): advisory, non-exclusive, with a TTL inside published caps.

``POST /claims`` checks the node against the committed frontier at ``main`` (present and
claimable; a refusal names why not, from the graph and the targets index — F05-T9), clamps
an undeclared TTL to the minimum, rejects one above the maximum, enforces the active-claim cap,
and returns the receipt — or, when the caller already holds an active claim on the node, that
claim again with ``200`` (F05-T14); every receipt names the node's other active holders.
``DELETE /claims/<id>`` releases the holder's own claim, and ``GET /claims/mine`` lists the
caller's active claims with their ids. Expiry is lazy: a claim past ``expires`` counts as
released wherever it is read.
"""

from __future__ import annotations

import logging
import re
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import clock as clockmod
from opn_api import frontier, pending, precheck, ratelimit
from opn_api import identity as identitymod
from opn_api.app import ApiError
from opn_api.store import Claim, Identity, release
from opn_gate import graph as graphmod
from opn_gate import intake

if TYPE_CHECKING:
    from opn_api.app import Context

log = logging.getLogger(__name__)

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


def others(ctx: Context, claim: Claim, claims: list[Claim]) -> list[dict[str, str]]:
    """F05-T14: the other active holders of ``claim``'s node, as the overlay shows them
    (``pseudonym``, ``expires``, the registry's order) — never the holder, never a claim that has
    expired or been released. Racing stays allowed (D-25); this only says who else is there."""
    now = clockmod.render(ctx.clock.now())
    names: dict[str, str] = {}
    out: list[dict[str, str]] = []
    for c in claims:
        same_node = c.node_id == claim.node_id and c.target_id == claim.target_id
        if not same_node or c.identity_id == claim.identity_id or not frontier.is_active(c, now):
            continue
        if c.identity_id not in names:
            holder = ctx.store.get_identity(c.identity_id)
            names[c.identity_id] = holder.pseudonym if holder else "?"
        out.append({"pseudonym": names[c.identity_id], "expires": c.expires})
    return sorted(out, key=lambda a: (a["expires"], a["pseudonym"]))


def held_receipt(ctx: Context, claim: Claim, pseudonym: str, claims: list[Claim]) -> dict[str, Any]:
    """A receipt for a claim its holder is looking at: the claim and who else holds the node."""
    return {**receipt(claim, pseudonym), "others": others(ctx, claim, claims)}


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
    """R7 (F05-T9): the node's claimable frontier entry, or a refusal that says why not —
    unknown, blocked (cause and unproved dependencies), otherwise not open (its status), or on
    the frontier but not claimable (the target's reasons from ``targets/index.json``)."""
    entries = [
        e
        for e in frontier.committed_frontier(ctx)["entries"]
        if e["node_id"] == node_id and (target_id is None or e["target_id"] == target_id)
    ]
    if not entries:
        raise off_frontier(ctx, node_id, target_id)
    if len(entries) > 1:
        raise ambiguous(node_id)
    entry: dict[str, Any] = entries[0]
    if not entry.get("claimable"):
        raise unclaimable(ctx, node_id, str(entry["target_id"]))
    return entry


def unclaimable(ctx: Context, node_id: str, target_id: str) -> ApiError:
    """A frontier entry that is not claimable. An open variant stays listed while it waits on its
    holes (F03-R5, T6), and that is ``node-blocked`` like any blocked node; otherwise the reasons
    are the target's. A graph that cannot be read gives the target's refusal, never a pass."""
    try:
        graph = precheck.graph_doc(ctx)
    except ApiError as exc:
        log.warning("claim refusal for %s without the graph: %s", node_id, exc.message)
        return not_claimable(ctx, node_id, target_id)
    row = next((n for n in graph.get(target_id, []) if n.get("node_id") == node_id), None)
    if row is not None:
        facts = precheck.facts_of(target_id, row)
        if facts["status"] == "blocked":
            return precheck.blocked_error(node_id, facts, graph)
    return not_claimable(ctx, node_id, target_id)


def circular(
    node_id: str,
    facts: dict[str, Any],
    *,
    lead: str | None = None,
    merged: tuple[str, ...] = (),
) -> ApiError:
    """F08-T17 (D-16): a node under a merged circularity claim is off the frontier by design. Its
    status is untouched (a proof of it is still a proof), so "ready and not on the frontier"
    would be true and useless; this names the reason and where the claim lives.

    F08-T18: ``POST /defect-claims`` refuses a second circularity claim in the same words, with
    its own ``lead`` and, when it could list them, the ``merged`` claims' paths."""
    where = (
        f"The claim and its Lean exhibit: {', '.join(merged)}."
        if merged
        else f"The claim and its Lean exhibit are under nodes/{node_id}/defects/."
    )
    details: dict[str, Any] = {"status": facts["status"], "cause": graphmod.CAUSE_CIRCULAR}
    if merged:
        details["claims"] = list(merged)
    return ApiError(
        409,
        "node-circular",
        f"{lead or f'{node_id} is not claimable'}: it is circular — a merged circularity claim "
        f"(D-16) proves a node above it implies it, so it is no easier than what it was meant to "
        f"reduce. {where}",
        details=details,
    )


def ambiguous(node_id: str) -> ApiError:
    return ApiError(409, "node-ambiguous", f"{node_id} exists in several targets; pass target_id")


def off_frontier(ctx: Context, node_id: str, target_id: str | None) -> ApiError:
    """A node the frontier does not list: what the graph says it is (D-25). Only the graph
    knows, because the frontier holds open nodes alone."""
    graph = precheck.graph_doc(ctx)
    rows = [
        (tid, node)
        for tid, nodes in graph.items()
        if target_id is None or tid == target_id
        for node in nodes
        if node["node_id"] == node_id
    ]
    if not rows:
        where = f" in target {target_id}" if target_id is not None else ""
        return pending.unknown_node(ctx, node_id, where)
    if len(rows) > 1:
        return ambiguous(node_id)
    facts = precheck.facts_of(*rows[0])
    if facts["cause"] == graphmod.CAUSE_CIRCULAR:
        return circular(node_id, facts)
    if facts["status"] == "blocked":
        if precheck.witness_awaits_render(ctx, node_id, facts):  # F06-T8: one state, one answer
            return precheck.awaits_render(node_id, f"{node_id}'s witness has merged")
        return precheck.blocked_error(node_id, facts, graph)
    details = precheck.standing(ctx, node_id, facts)
    successor = f" {details['replacement']} replaced it." if details["replacement"] else ""
    return ApiError(
        409,
        "node-not-open",
        f"{node_id} is {facts['status']} and not on the frontier at main; only an open node on "
        f"the frontier can be claimed (D-25).{successor}",
        details=details,
    )


def not_claimable_reasons(ctx: Context, target_id: str) -> list[str]:
    """The target's ``not_claimable`` list as ``targets/index.json`` publishes it (F11-R4). The
    refusal stands without it: an index that cannot be read, or a row with no list, gives none."""
    try:
        index = precheck.index_doc(ctx)
    except ApiError as exc:
        log.warning("claim refusal for %s without reasons: %s", target_id, exc.message)
        return []
    row = next((t for t in index.get("targets", []) if t.get("target_id") == target_id), None)
    reasons = row.get("not_claimable") if isinstance(row, dict) else None
    return [str(r) for r in reasons] if isinstance(reasons, list) else []


def not_claimable(ctx: Context, node_id: str, target_id: str) -> ApiError:
    """``409 node-not-claimable`` in the words the Targets page uses, one per reason (F05-T9)."""
    reasons = not_claimable_reasons(ctx, target_id)
    message = f"{node_id} is not claimable"
    if reasons:
        message += ": " + "; ".join(intake.explain(r) for r in reasons)
    return ApiError(409, "node-not-claimable", message, details={"not_claimable": reasons})


def active_for(ctx: Context, identity_id: str) -> list[Claim]:
    now = clockmod.render(ctx.clock.now())
    return [
        c
        for c in ctx.store.list_claims()
        if c.identity_id == identity_id and frontier.is_active(c, now)
    ]


def held_on(held: list[Claim], node_id: str, target_id: str) -> Claim | None:
    """F05-T14: the active claim, among the caller's ``held``, on this node of this target."""
    return next((c for c in held if c.node_id == node_id and c.target_id == target_id), None)


#: F05-T8: the fields ``POST /claims`` reads; any other top-level key is refused.
CLAIM_FIELDS: tuple[str, ...] = ("node_id", "target_id", "ttl_hours")


async def post_claims(ctx: Context, request: Request) -> Response:
    identity: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, CLAIM_FIELDS)
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
    # F05-T14: one claim per holder per node. A repeat is the claim already held, unchanged and
    # not charged against the cap; once it is released or expired, a new claim is a new id.
    existing = held_on(held, node_id, str(entry["target_id"]))
    if existing is not None:
        return JSONResponse(
            held_receipt(ctx, existing, identity.pseudonym, ctx.store.list_claims())
        )
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
    return JSONResponse(
        held_receipt(ctx, claim, identity.pseudonym, ctx.store.list_claims()), status_code=201
    )


async def get_my_claims(ctx: Context, request: Request) -> Response:
    """F05-T14 (ruling D3(b)): the caller's active claims with their ids, oldest first, each with
    the other holders of its node. The public registry publishes pseudonyms and expiry only
    (``claims/v1``), so without this a lost receipt made a claim unreleasable until it expired."""
    identity: Identity = request.state.identity
    claims = ctx.store.list_claims()
    mine = sorted(active_for(ctx, identity.id), key=lambda c: c.id)
    return JSONResponse(
        {
            "pseudonym": identity.pseudonym,
            "snapshot_at": clockmod.render(ctx.clock.now()),
            "claims": [held_receipt(ctx, c, identity.pseudonym, claims) for c in mine],
        }
    )


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
