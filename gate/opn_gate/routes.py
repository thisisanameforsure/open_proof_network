"""Routes and sufficient sets, read from a target's products (F27; D-25 v3.40).

A target is an AND-OR graph. A merged decomposition of a node (D-12 #5, D-31) is a *route*:
every one of its holes is needed (AND). A node's routes, a direct proof of it, and at the root
each ``resolves`` variant (D-30) are alternatives, any one of which closes it (OR). A *sufficient
set* is a set of statements whose proofs, together with the closing proofs of the nodes its routes
pass through (its *assemblies*: a decomposed node stays open until its own closing artifact
merges, D-12 v3.19), would close the root.

Everything here is derived from two published products and nothing else: a target's
``graph.json`` (its nodes, their statuses, deps, origins, relations and ``decompositions``) and
the entries ``frontier.json`` carries for it (attempts, refuted route classes, ``ready_since``,
D-13, D-25). Nothing is recorded, so the MCP tool and the site read the same function over the same
documents and cannot disagree (F27-Q1).

The published sets are the *finest* cuts: an open node is expanded into each of its live routes
and taken directly only where none is live; a proved node ends the cut as a closed member. With
``cut="any"`` an open node is also taken directly in place of its routes, which yields every
coarser cut (F27-Q2). The finest cuts are every full expansion, one per choice of routes, even
one whose open statements strictly contain another's (F27-T7, the owner's ruling); among the
coarser cuts only minimal sets are kept, since a set containing another says nothing the smaller
one does not. Sets are listed in the order the record
gives them — the root's routes in their merge order, then a direct proof, then the variants — and
never ranked (D-25).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import product
from typing import Any, Literal

from opn_gate.graph import HOLE_ORIGINS, HOLE_SEPARATOR

Cut = Literal["finest", "any"]
CUTS: tuple[str, ...] = ("finest", "any")

#: The most sets one enumeration returns (F27-R8). A documented default; the service may pass its
#: own (``OPN_API_ROUTES_MAX_SETS``). The finest cuts of every live target number two or fewer
#: (2026-10-15); the coarser cuts of erdos-1094 number 225.
DEFAULT_MAX_SETS = 1000
#: How many candidate options one node may gather, as a multiple of the cap, before the dominated
#: ones are dropped (F27-T6); past it the answer says it was cut short.
RAW_FACTOR = 10

PROVED = "proved"
#: A node in one of these closes nothing: a refutation or a vacuity certificate settled it the
#: other way (D-12), a curator abandoned it (D-14), or a revision replaced it (D-8).
DEAD_STATUSES: frozenset[str] = frozenset({"refuted", "defective", "abandoned", "superseded"})
RESOLVES = "resolves"

_REVISION_RE = re.compile(r"-v\d+$")


# --- the record, read --------------------------------------------------------------------------


@dataclass(frozen=True)
class Hole:
    """One hole of a route: its name in the partial, the node it became (``None`` when the record
    does not say, F27-R2), and the facts the frontier publishes for that node."""

    name: str
    node: str | None
    status: str | None
    attempts: int | None  # None: the node is not on the frontier, so nothing is published
    refuted_route_classes: tuple[str, ...]
    ready_since: str | None
    routes: int  # how many routes of its own the hole's node has

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "node": self.node,
            "status": self.status,
            "attempts": self.attempts,
            "refuted_route_classes": list(self.refuted_route_classes),
            "ready_since": self.ready_since,
            "routes": self.routes,
        }


@dataclass(frozen=True)
class Summary:
    """F27-R4: a route's holes, aggregated. ``attempts`` and ``unattempted`` count the open holes
    the frontier lists; ``oldest_open_since`` is the earliest ``ready_since`` among them."""

    holes: int
    proved: int
    open: int
    dead: int
    unresolved: int
    attempts: int
    unattempted: int
    refuted_route_classes: tuple[str, ...]
    oldest_open_since: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "holes": self.holes,
            "proved": self.proved,
            "open": self.open,
            "dead": self.dead,
            "unresolved": self.unresolved,
            "attempts": self.attempts,
            "unattempted": self.unattempted,
            "refuted_route_classes": list(self.refuted_route_classes),
            "oldest_open_since": self.oldest_open_since,
        }


@dataclass(frozen=True)
class Route:
    """One merged decomposition of ``node``, ``id`` ``<node>@<k>`` for its ``k``-th in the record's
    order (append-only, so an id never moves)."""

    id: str
    node: str
    partial: str
    holes: tuple[Hole, ...]
    summary: Summary

    @property
    def resolved(self) -> bool:
        return all(h.node is not None for h in self.holes)

    @property
    def live(self) -> bool:
        """Resolved, and no hole is dead: the enumeration may expand it."""
        return self.resolved and not any(h.status in DEAD_STATUSES for h in self.holes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node": self.node,
            "partial": self.partial,
            "resolved": self.resolved,
            "live": self.live,
            "holes": [h.as_dict() for h in self.holes],
            "summary": self.summary.as_dict(),
        }


@dataclass(frozen=True)
class SufficientSet:
    """F27-R7: one cut. ``statements`` is the set (proved and open, sorted); ``assemblies`` the
    interior nodes its routes pass through, each still needing its closing proof; ``routes`` the
    routes it uses, in the order the enumeration met them, the root's first; ``shared`` how many
    of its statements another set also holds."""

    id: str
    statements: tuple[str, ...]
    proved: tuple[str, ...]
    open: tuple[str, ...]
    assemblies: tuple[str, ...]
    routes: tuple[str, ...]
    variant: str | None
    shared: int
    circular: tuple[str, ...]

    @property
    def total(self) -> int:
        return len(self.statements)

    @property
    def closed(self) -> int:
        return len(self.proved)

    @property
    def remaining(self) -> int:
        return len(self.open)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "statements": list(self.statements),
            "proved": list(self.proved),
            "open": list(self.open),
            "assemblies": list(self.assemblies),
            "routes": list(self.routes),
            "variant": self.variant,
            "total": self.total,
            "closed": self.closed,
            "remaining": self.remaining,
            "shared": self.shared,
            "circular": list(self.circular),
        }


@dataclass(frozen=True)
class Routes:
    target_id: str
    root: str
    cut: str
    truncated: bool
    routes: tuple[Route, ...]
    sets: tuple[SufficientSet, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "root": self.root,
            "cut": self.cut,
            "truncated": self.truncated,
            "routes": [r.as_dict() for r in self.routes],
            "sets": [s.as_dict() for s in self.sets],
        }


# --- reading the products ----------------------------------------------------------------------


def _rows(graph: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {str(n["node_id"]): n for n in graph.get("nodes") or [] if isinstance(n, Mapping)}


def _entries(
    frontier_entries: Iterable[Mapping[str, Any]], target_id: str
) -> dict[str, Mapping[str, Any]]:
    """The frontier's entries for this target, by node. An entry naming no target is taken as
    this target's (a caller may pass one target's entries already filtered)."""
    out: dict[str, Mapping[str, Any]] = {}
    for e in frontier_entries:
        if e.get("target_id") not in (None, target_id):
            continue
        out[str(e["node_id"])] = e
    return out


def _is_hole_child(parent: str, node_id: str, rows: Mapping[str, Mapping[str, Any]]) -> bool:
    """``graph.is_hole_of`` over the published row: the id carries the parent's prefix and the
    row's origin is a hole's."""
    row = rows.get(node_id)
    return (
        row is not None
        and node_id.startswith(parent + HOLE_SEPARATOR)
        and str(row.get("origin")) in HOLE_ORIGINS
    )


def _follow(
    node_id: str, parent: Mapping[str, Any], rows: Mapping[str, Mapping[str, Any]]
) -> str | None:
    """F27-R3: a hole the record names, as the statement that now carries it. ``graph.json``
    already reads holes through revisions (``decompositions_of``), so this matters only for an
    older or hand-made product: a superseded hole is replaced by the one revision of it (D-8,
    spelled ``<id>-v<n>``, F08-Q16) that is not itself superseded, preferring the parent's dep."""
    row = rows.get(node_id)
    if row is None:
        return None
    if str(row.get("status")) != "superseded":
        return node_id
    base = _REVISION_RE.sub("", node_id)
    live = [
        k
        for k, r in rows.items()
        if _REVISION_RE.sub("", k) == base and str(r.get("status")) != "superseded"
    ]
    deps = {str(d) for d in parent.get("deps") or []}
    preferred = [k for k in live if k in deps]
    pick = preferred or live
    return pick[0] if len(pick) == 1 else None


def _hole_nodes(
    node_id: str, rows: Mapping[str, Mapping[str, Any]]
) -> list[tuple[str, list[tuple[str, str | None]]]]:
    """Each route of ``node_id`` as ``(partial, [(hole name, node or None)])``, with F27-R2's
    assignment of unnamed holes applied where it is unambiguous."""
    row = rows[node_id]
    out: list[tuple[str, list[tuple[str, str | None]]]] = []
    for d in row.get("decompositions") or []:
        holes: list[tuple[str, str | None]] = []
        for h in d.get("holes") or []:
            raw = h.get("node")
            holes.append((str(h.get("name")), _follow(str(raw), row, rows) if raw else None))
        out.append((str(d.get("partial")), holes))
    unnamed = [k for k, (_, holes) in enumerate(out) if any(n is None for _, n in holes)]
    if len(unnamed) == 1:
        taken = {n for _, holes in out for _, n in holes if n is not None}
        children = [
            str(dep)
            for dep in row.get("deps") or []
            if _is_hole_child(node_id, str(dep), rows) and str(dep) not in taken
        ]
        k = unnamed[0]
        partial, holes = out[k]
        gaps = [i for i, (_, n) in enumerate(holes) if n is None]
        if len(gaps) == len(children):
            filled = list(holes)
            for i, child in zip(gaps, children, strict=True):
                filled[i] = (filled[i][0], child)
            out[k] = (partial, filled)
    return out


def _route_of(  # noqa: PLR0913 — the route's place, its holes and the facts it aggregates
    node_id: str,
    *,
    k: int,
    partial: str,
    holes: list[tuple[str, str | None]],
    rows: Mapping[str, Mapping[str, Any]],
    entries: Mapping[str, Mapping[str, Any]],
) -> Route:
    made: list[Hole] = []
    for name, nid in holes:
        row = rows.get(nid) if nid else None
        entry = entries.get(nid) if nid else None
        made.append(
            Hole(
                name=name,
                node=nid,
                status=str(row.get("status")) if row is not None else None,
                attempts=int(entry.get("attempts") or 0) if entry is not None else None,
                refuted_route_classes=tuple(
                    str(c) for c in (entry.get("refuted_route_classes") or [])
                )
                if entry is not None
                else (),
                ready_since=entry.get("ready_since") if entry is not None else None,
                routes=len(row.get("decompositions") or []) if row is not None else 0,
            )
        )
    proved = sum(1 for h in made if h.status == PROVED)
    dead = sum(1 for h in made if h.status in DEAD_STATUSES)
    unresolved = sum(1 for h in made if h.node is None)
    open_holes = [
        h
        for h in made
        if h.node is not None and h.status != PROVED and h.status not in DEAD_STATUSES
    ]
    listed = [h for h in open_holes if h.attempts is not None]
    since = sorted(str(h.ready_since) for h in open_holes if h.ready_since)
    summary = Summary(
        holes=len(made),
        proved=proved,
        open=len(open_holes),
        dead=dead,
        unresolved=unresolved,
        attempts=sum(h.attempts or 0 for h in listed),
        unattempted=sum(1 for h in listed if h.attempts == 0),
        refuted_route_classes=tuple(sorted({c for h in made for c in h.refuted_route_classes})),
        oldest_open_since=since[0] if since else None,
    )
    return Route(f"{node_id}@{k}", node_id, partial, tuple(made), summary)


# --- the enumeration ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Option:
    """One way to close a node: the statements taken (proved or open), the nodes assembled on the
    way, the routes used (the outermost first) and the resolves variant gone through, if any."""

    members: frozenset[str]
    assemblies: tuple[str, ...] = ()
    routes: tuple[str, ...] = ()
    variant: str | None = None

    def key(self) -> tuple[frozenset[str], frozenset[str]]:
        return self.members, frozenset(self.assemblies)


def _ordered(*parts: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(x for p in parts for x in p))


@dataclass
class _Enumerator:
    rows: Mapping[str, Mapping[str, Any]]
    routes_by_node: Mapping[str, Sequence[Route]]
    cut: str
    max_sets: int
    truncated: bool = False
    memo: dict[str, list[_Option]] = field(default_factory=dict)

    def status(self, node_id: str) -> str:
        return str(self.rows[node_id].get("status"))

    def combine(self, parts: Sequence[Sequence[_Option]]) -> Iterator[_Option]:
        if any(not p for p in parts):
            return
        for combo in product(*parts):
            variants = [o.variant for o in combo if o.variant]
            yield _Option(
                members=frozenset().union(*(o.members for o in combo)),
                assemblies=_ordered(*(o.assemblies for o in combo)),
                routes=_ordered(*(o.routes for o in combo)),
                variant=variants[0] if variants else None,
            )

    def bounded(self, options: Iterable[_Option]) -> list[_Option]:
        """The minimal options, deduplicated, and no more than the cap; past it the enumeration
        says it was cut. F27-T6: dominated options are dropped here, at every node, before the
        cap is applied: an option whose open statements strictly contain another's stays
        dominated under any union with the same other parts, so dropping it early loses no
        minimal set, and the cap then counts minimal sets rather than the combinations met on the
        way (live erdos-1094, 2026-10-15: 293 minimal coarser sets, cut to 58 before this)."""
        out: dict[tuple[frozenset[str], frozenset[str]], _Option] = {}
        ceiling = self.max_sets * RAW_FACTOR
        for o in options:
            if len(out) >= ceiling:
                self.truncated = True
                break
            out.setdefault(o.key(), o)
        # F27-T7 (the owner, 2026-10-15): the finest cuts keep every full expansion, one per
        # choice of routes, even one that needs strictly more than another; only the coarser cuts,
        # which number in the hundreds, keep the minimal ones alone.
        kept = _minimal(list(out.values()), self.rows) if self.cut == "any" else list(out.values())
        if len(kept) > self.max_sets:
            self.truncated = True
            kept = kept[: self.max_sets]
        return kept

    def close(self, node_id: str, path: frozenset[str]) -> tuple[list[_Option], bool]:
        """Every way to close ``node_id``, and whether a cycle was cut on the way (an answer that
        cut a cycle depends on the path and is not remembered)."""
        if node_id not in self.rows:
            return [], False
        status = self.status(node_id)
        if status == PROVED:
            return [_Option(frozenset([node_id]))], False
        if status in DEAD_STATUSES:
            return [], False
        if node_id in path:
            return [], True
        if node_id in self.memo:
            return self.memo[node_id], False
        path = path | {node_id}
        cyclic = False
        row = self.rows[node_id]
        expanded: list[_Option] = []
        for route in self.routes_by_node.get(node_id, ()):
            if not route.live:
                continue
            parts: list[list[_Option]] = []
            for h in route.holes:
                opts, cut_here = self.close(str(h.node), path)
                cyclic = cyclic or cut_here
                parts.append(opts)
            expanded.extend(
                _Option(
                    o.members,
                    _ordered((node_id,), o.assemblies),
                    _ordered((route.id,), o.routes),
                    o.variant,
                )
                for o in self.combine(parts)
            )
        direct: list[_Option] = []
        if self.cut == "any" or not expanded:
            holes = {str(h.node) for r in self.routes_by_node.get(node_id, ()) for h in r.holes}
            needs: list[list[_Option]] = [[_Option(frozenset([node_id]))]]
            for raw in row.get("deps") or []:
                dep = str(raw)
                if dep in holes or _is_hole_child(node_id, dep, self.rows):
                    continue  # a decomposition never blocks its node (D-12 v3.19)
                opts, cut_here = self.close(dep, path)
                cyclic = cyclic or cut_here
                needs.append(opts)
            direct = list(self.combine(needs))
        options = self.bounded([*expanded, *direct])
        if not cyclic:
            self.memo[node_id] = options
        return options, cyclic


def _minimal(options: list[_Option], rows: Mapping[str, Mapping[str, Any]]) -> list[_Option]:
    """F27-R6: drop a set whose open statements strictly contain another's; keep the first of
    sets with the same open statements."""

    def open_of(o: _Option) -> frozenset[str]:
        return frozenset(m for m in o.members if str(rows[m].get("status")) != PROVED)

    opens = [open_of(o) for o in options]
    kept: dict[frozenset[str], _Option] = {}
    for o, mine in zip(options, opens, strict=True):
        if any(other < mine for other in opens):
            continue
        kept.setdefault(mine, o)
    return list(kept.values())


def _set_id(o: _Option) -> str:
    body = json.dumps([sorted(o.members), sorted(o.assemblies)], separators=(",", ":"))
    return "s-" + hashlib.sha256(body.encode("utf-8")).hexdigest()[:10]


def read(
    graph: Mapping[str, Any],
    frontier_entries: Iterable[Mapping[str, Any]] = (),
    *,
    cut: str = "finest",
    max_sets: int = DEFAULT_MAX_SETS,
) -> Routes:
    """A target's routes and sufficient sets from its ``graph.json`` and its frontier entries."""
    if cut not in CUTS:
        msg = f"unknown cut {cut!r}: expected one of {', '.join(CUTS)}"
        raise ValueError(msg)
    rows = _rows(graph)
    target_id = str(graph.get("target_id"))
    root = str(graph.get("root"))
    entries = _entries(frontier_entries, target_id)
    by_node: dict[str, list[Route]] = {}
    for node_id in rows:
        for k, (partial, holes) in enumerate(_hole_nodes(node_id, rows), start=1):
            by_node.setdefault(node_id, []).append(
                _route_of(node_id, k=k, partial=partial, holes=holes, rows=rows, entries=entries)
            )
    # The record's order: the products list nodes sorted, and each node's routes in merge order.
    all_routes = tuple(r for node_id in rows for r in by_node.get(node_id, ()))
    walker = _Enumerator(rows, by_node, cut, max(1, max_sets))
    options: list[_Option] = []
    if root in rows:
        options, _ = walker.close(root, frozenset())
        if walker.status(root) != PROVED:
            for vid, row in rows.items():
                if vid == root or row.get("relation") != RESOLVES:
                    continue
                via, _ = walker.close(vid, frozenset())
                options.extend(
                    _Option(o.members, o.assemblies, o.routes, o.variant or vid) for o in via
                )
    minimal = walker.bounded(options)
    held: dict[str, int] = {}
    for o in minimal:
        for m in o.members:
            held[m] = held.get(m, 0) + 1
    sets = tuple(
        SufficientSet(
            id=_set_id(o),
            statements=tuple(sorted(o.members)),
            proved=tuple(sorted(m for m in o.members if str(rows[m].get("status")) == PROVED)),
            open=tuple(sorted(m for m in o.members if str(rows[m].get("status")) != PROVED)),
            assemblies=o.assemblies,
            routes=o.routes,
            variant=o.variant,
            shared=sum(1 for m in o.members if held[m] > 1),
            circular=tuple(sorted(m for m in o.members if rows[m].get("circular"))),
        )
        for o in minimal
    )
    return Routes(target_id, root, cut, walker.truncated, all_routes, sets)
