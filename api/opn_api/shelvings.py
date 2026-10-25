"""``POST /shelvings`` (D-14, D-32, D-35 v3.47; F31-T7, R6).

A steward of the node's target or a listed curator takes a statement off the root's path — or
one merged decomposition of it, or lifts such a judgment — from the site (the F23 web session)
or with a bearer whose identity is a GitHub login. The service writes a ``shelving/v1`` record as
that login and signs it with the network's approval key over the canonical body the gate
verifies, exactly as ``POST /literature/confirm`` does; the gate checks the signer's role again
at the merge. One signer, no second review (F31-Q1).

Shelving is a judgment, not a status (F31-Q4, Q7): the record changes no ``status``, the products
derive ``shelved`` on the row, and the service refuses here only what the gate would refuse at
the merge or what the row already says: the root (``node-root``), a statement a merged proof uses
(``node-used``: ``proofs[].used`` or a ``closure`` input on any row of the target), a route that
is not one of the node's merged decompositions (``shelving-route-unknown``), and an act that
changes nothing (``already-shelved`` / ``not-shelved``). An ``unshelved`` record on a node shelved
only by inheritance is allowed: it is how a hole child is exempted (F31-Q3), so ``not-shelved``
is judged only when the row carries no shelving at all. The cause is a person's words and is
written to the record alone (C9).
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

import yaml
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from opn_api import appends, frontier, ratelimit, stewards, submissions
from opn_api import clock as clockmod
from opn_api import identity as identitymod
from opn_api.app import ApiError

if TYPE_CHECKING:
    from opn_api.app import Context
    from opn_api.store import Identity

SCHEMA = "shelving/v1"
DIR = "shelving"
KIND = "shelving"
ACTIONS: tuple[str, ...] = ("shelved", "unshelved")
SCOPES: tuple[str, ...] = ("node", "route")
#: F05-T8: what ``POST /shelvings`` reads; any other top-level key is refused.
FIELDS: tuple[str, ...] = ("node_id", "action", "scope", "route", "cause")
#: The schema's bounds on a cause, named here so the refusal can say them.
CAUSE_MAX = 1000
#: A route named as the record names one: a partial's file relative to the node.
ROUTE_RE = re.compile(r"^attempts/[^/]+\.lean$")


def bad(message: str, field: str) -> ApiError:
    return ApiError(400, "arguments-invalid", message, details={"field": field})


# --- the body ------------------------------------------------------------------------------------


def checked_action(raw: Any) -> str:
    if raw not in ACTIONS:
        raise bad("action is shelved or unshelved (D-14 v3.47)", "action")
    return str(raw)


def checked_scope(raw: Any) -> str:
    if raw not in SCOPES:
        raise bad(
            "scope is node (the statement and its hole children) or route (one merged "
            "decomposition of it, named in route)",
            "scope",
        )
    return str(raw)


def checked_route(scope: str, raw: Any) -> str | None:
    if scope == "node":
        if raw is not None:
            raise bad("route is null when scope is node; name a route with scope route", "route")
        return None
    if not isinstance(raw, str) or not ROUTE_RE.match(raw) or ".." in raw:
        raise bad(
            "route is the partial's file relative to the node, attempts/<file>.lean, as the "
            "node's decompositions name it",
            "route",
        )
    return raw


def checked_cause(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip() or len(raw) > CAUSE_MAX:
        raise bad(f"cause is your published reasoning, 1 to {CAUSE_MAX} characters", "cause")
    return raw


# --- the row ------------------------------------------------------------------------------------


def target_rows(ctx: Context, target_id: str) -> tuple[str | None, dict[str, dict[str, Any]]]:
    """The target's declared root and its rows by id, from the committed ``graph.json``."""
    doc = json.loads(frontier.committed(ctx, f"targets/{target_id}/graph.json"))
    root = doc.get("root")
    rows = {str(n.get("node_id")): n for n in doc.get("nodes", []) if isinstance(n, dict)}
    return (str(root) if isinstance(root, str) else None), rows


def users_of(rows: dict[str, dict[str, Any]], node_id: str) -> list[str]:
    """The nodes whose merged proofs use ``node_id`` (``proofs[].used``, F18) or whose closure
    link takes it as an input (F28): such a statement is a fact a proof rests on."""
    out = []
    for other, row in rows.items():
        used = {
            str(u)
            for proof in row.get("proofs") or []
            if isinstance(proof, dict)
            for u in proof.get("used") or []
        }
        closure = row.get("closure")
        if isinstance(closure, dict):
            used |= {str(u) for u in closure.get("inputs") or []}
        if node_id in used:
            out.append(other)
    return sorted(out)


def routes_of(row: dict[str, Any]) -> list[str]:
    return [
        str(d["partial"])
        for d in row.get("decompositions") or []
        if isinstance(d, dict) and d.get("partial")
    ]


def route_holes(row: dict[str, Any], route: str) -> list[str]:
    for d in row.get("decompositions") or []:
        if isinstance(d, dict) and d.get("partial") == route:
            return [str(h["node"]) for h in d.get("holes") or [] if h.get("node")]
    return []


def retired_through(rows: dict[str, dict[str, Any]], node_id: str, route: str) -> bool:
    """Whether the route already reads retired: every hole node it made is shelved through this
    node's own route-scope record. A route with no hole node on the record retires nothing yet,
    so it is never already retired."""
    holes = route_holes(rows[node_id], route)
    if not holes:
        return False
    for hole in holes:
        shelved = (rows.get(hole) or {}).get("shelved")
        if not isinstance(shelved, dict):
            return False
        if shelved.get("scope") != "route" or shelved.get("via") != node_id:
            return False
    return True


def check_act(  # noqa: PLR0913 — one act, every rule
    ctx: Context, target_id: str, node_id: str, *, action: str, scope: str, route: str | None
) -> None:
    """The refusals the gate would make at the merge, or the row already answers: the root, a
    used statement, an unknown route, and an act that changes nothing."""
    root, rows = target_rows(ctx, target_id)
    row = rows.get(node_id)
    if row is None:
        # Listed on the frontier but on no row (F05-T9's case): nothing to judge against.
        return
    # F31-Q18: a retirement sits on the node whose decomposition it names and never shelves
    # that node, so the root's own routes are retired like any other's; the rule is scope node.
    if node_id == root and scope == "node":
        raise ApiError(
            409,
            "node-root",
            f"{node_id} is the root of {target_id}; the root is never shelved (D-14 v3.47), and "
            "a problem is retired by its target's status, not here",
            details={"node_id": node_id, "target_id": target_id},
        )
    if scope == "route":
        assert route is not None
        known = routes_of(row)
        if route not in known:
            raise ApiError(
                404,
                "shelving-route-unknown",
                f"{route} is not a merged decomposition of {node_id}; a route is named by its "
                "partial's file as the row's decompositions list them",
                details={"node_id": node_id, "route": route, "routes": known},
            )
    if action == "shelved":
        used_by = users_of(rows, node_id)
        if used_by:
            raise ApiError(
                409,
                "node-used",
                f"{node_id} is used by a merged proof of {', '.join(used_by)}; a statement a "
                "kernel-checked proof rests on is a fact and cannot be shelved (D-14 v3.47)",
                details={"node_id": node_id, "used_by": used_by},
            )
    shelved = row.get("shelved") if isinstance(row.get("shelved"), dict) else None
    if action == "shelved":
        already = (
            retired_through(rows, node_id, route)
            if scope == "route" and route is not None
            else shelved is not None
            and shelved.get("via") == node_id
            and shelved.get("scope") == "node"
        )
        if already:
            what = (
                f"route {route} of {node_id} is already retired"
                if scope == "route"
                else (f"{node_id} is already shelved by its own record")
            )
            raise ApiError(
                409,
                "already-shelved",
                f"{what}; the products say so and a second record would change nothing",
                details={"node_id": node_id, "shelved": shelved, "route": route},
            )
    elif shelved is None and not (
        scope == "route" and route is not None and retired_through(rows, node_id, route)
    ):
        raise ApiError(
            409,
            "not-shelved",
            f"{node_id} is not shelved; an unshelved record lifts a shelving the products "
            "publish on the row (its own, or one it inherits)",
            details={"node_id": node_id, "route": route},
        )


# --- the record ----------------------------------------------------------------------------------


def record_path(target_id: str, node_id: str, stamp: str, contributor: str) -> str:
    return appends.node_dir(target_id, node_id) + f"{DIR}/{stamp}-{contributor}.yaml"


def render(doc: dict[str, Any]) -> str:
    """The file as it lands: the schema's field order, so a reader meets the act first."""
    return str(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))


def verb(action: str, scope: str) -> str:
    if action == "unshelved":
        return "route unretired" if scope == "route" else "unshelved"
    return "route retired" if scope == "route" else "shelved"


async def post_shelvings(ctx: Context, request: Request) -> Response:
    """R6: one signed record, by the approval key, in its own pull request. The signer is the
    session's or the bearer's GitHub login (``stewards.github_login``), the key is read where
    ``POST /stewards`` reads it, and the body is signed as every approval-key record is."""
    held: Identity = request.state.identity
    fields, _ = await identitymod.body_fields(request, FIELDS)
    login = stewards.github_login(held)
    action = checked_action(fields.get("action"))
    scope = checked_scope(fields.get("scope"))
    route = checked_route(scope, fields.get("route"))
    cause = checked_cause(fields.get("cause"))
    node_id, target_id = appends.node_target(ctx, fields)
    private, public = stewards.approval_key(ctx)
    ratelimit.enforce(
        ctx,
        "shelving",
        login.casefold(),
        limit=ctx.settings.approvals_per_hour,
        seconds=ratelimit.HOUR_S,
    )
    stewards.may_act(ctx, target_id, login, "shelve a statement or retire a route (D-14 v3.47)")
    check_act(ctx, target_id, node_id, action=action, scope=scope, route=route)
    doc = stewards.sign_record(
        {
            "schema": SCHEMA,
            "node": node_id,
            "action": action,
            "scope": scope,
            "route": route,
            "cause": cause,
            "contributor": login,
            "date": clockmod.render(ctx.clock.now()),
            "via": stewards.VIA,
        },
        private,
        public,
    )
    appends.validated(doc, SCHEMA)
    path = record_path(target_id, node_id, appends.stamp(ctx), login)
    body = appends.append_pr(
        ctx,
        held,
        path=path,
        content=render(doc),
        subject=f"shelving: {node_id} {verb(action, scope)} by {login}",
        what="shelving",
        kind=KIND,
        target_id=target_id,
        node_id=node_id,
        written=f"{node_id} {action} {scope} {route}",
        extra_body=(
            f"\nThis record retires one merged decomposition of `{node_id}`, `{route}`: its "
            "holes leave the frontier and the drawing; the node itself does not (D-14 v3.47).\n"
            if scope == "route" and action == "shelved"
            else ""
        ),
    )
    return JSONResponse(stewards.receipt(body, submissions.APPEND_BRANCH_PREFIX), status_code=201)
