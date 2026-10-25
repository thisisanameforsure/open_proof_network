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

A route settles either way (D-25 v3.46, F27-T11): each set says whether it ``proves`` the root
(the sets above) or ``refutes`` it — a set closing a ``refutes`` variant (D-30 v3.46), enumerated
from that variant's routes exactly as the root's are from its own. The proving sets come first,
then the refuting ones, each side in the record's order; minimality is judged within a side and
the cap counts both. A false member of a set refutes nothing: it kills its route, no more.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from itertools import product
from typing import Any, Literal

from opn_gate.graph import HOLE_ORIGINS, HOLE_SEPARATOR

Cut = Literal["finest", "any"]
CUTS: tuple[str, ...] = ("finest", "any")
#: F27-R13: what the enumeration does at a proved statement. ``stop`` (the default, R5): the
#: statement is a closed member and nothing beneath it is listed. ``follow``: the statement is
#: expanded along what its proof's term rests on (F18-R2, ``proofs[0].used``), transitively, so
#: the set also lists the proved structure the proof already stands on. The sets are the same
#: either way — the same ids, open statements, assemblies, routes and order — because the cut is
#: still made at the proved statement; ``follow`` only adds what is beneath it.
AtProved = Literal["stop", "follow"]
AT_PROVED: tuple[str, ...] = ("stop", "follow")

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
#: D-30 v3.46: a variant whose proof refutes the root; its sets are the other side's (F27-T11).
REFUTES = "refutes"
#: The two sides a sufficient set may settle (D-25 v3.46): ``SufficientSet.settles``.
PROVES = "proves"
SIDES: tuple[str, ...] = (PROVES, REFUTES)

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
    label: str | None = None  # F29-R8: the node's label as graph.json carries it (v12)
    shelved: bool = False  # F31-R4 (D-14 v3.47): the node's row carries a shelving (graph/v15)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
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
    approach: str | None = None  # F29-R8: the decomposition's approach (graph/v12, R4)
    retired: bool = False  # F31-R4 (D-14 v3.47): a steward or curator retired the decomposition

    @property
    def resolved(self) -> bool:
        return all(h.node is not None for h in self.holes)

    @property
    def live(self) -> bool:
        """Resolved, not retired, and no hole is dead or shelved-and-unproved: the enumeration
        may expand it. F31-R4, Q6 (D-14 v3.47): a shelved *proved* hole keeps its route — a
        kernel-checked proof is a fact — while a retirement, or a shelved open hole, kills it."""
        return (
            self.resolved
            and not self.retired
            and not any(
                h.status in DEAD_STATUSES or (h.shelved and h.status != PROVED) for h in self.holes
            )
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node": self.node,
            "partial": self.partial,
            "approach": self.approach,
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
    #: F27-R13: the routes the proofs of its proved statements went through, when followed
    #: (``at_proved: follow``); empty when the enumeration stopped at them. Never a choice the
    #: set makes, so never read by the selector tree.
    proof_routes: tuple[str, ...] = ()
    #: D-25 v3.46 (F27-T11): which way the set settles the root — ``proves`` (the root's own
    #: routes, its direct proof, a resolves variant) or ``refutes`` (a set closing a refutes
    #: variant, D-30 v3.46).
    settles: str = PROVES

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
            "proof_routes": list(self.proof_routes),
            "variant": self.variant,
            "settles": self.settles,
            "total": self.total,
            "closed": self.closed,
            "remaining": self.remaining,
            "shared": self.shared,
        }


@dataclass(frozen=True)
class Routes:
    target_id: str
    root: str
    cut: str
    truncated: bool
    routes: tuple[Route, ...]
    sets: tuple[SufficientSet, ...]
    at_proved: str = "stop"

    def as_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "root": self.root,
            "cut": self.cut,
            "at_proved": self.at_proved,
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


def _text_or_none(raw: Any) -> str | None:
    return str(raw) if isinstance(raw, str) and raw else None


def _shelved(row: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    """F31-R3: the row's ``shelved`` object (graph/v15), or ``None`` — on a product that predates
    the field too, so an older graph shelves nothing."""
    found = row.get("shelved") if row is not None else None
    return found if isinstance(found, Mapping) else None


def _retired(
    node_id: str, holes: Sequence[str | None], rows: Mapping[str, Mapping[str, Any]]
) -> bool:
    """F31-R4: whether a route of ``node_id`` was retired (a ``scope: route`` record on the
    node). ``graph/v15`` publishes the shelving on the rows the record reached, not on the
    decomposition, so a retirement is read off its holes: one carrying a route-scope shelving
    whose ``via`` is this node. A retired route every hole of which another live route still
    needs leaves no mark and reads as live (F31, gate agent's note: a ``retired`` field on
    ``decompositions[]`` in the next graph version would make this exact)."""
    for hole in holes:
        found = _shelved(rows.get(hole) if hole else None)
        if found is not None and found.get("scope") == "route" and found.get("via") == node_id:
            return True
    return False


def _approaches(node_id: str, rows: Mapping[str, Mapping[str, Any]]) -> list[str | None]:
    """F29-R8: each decomposition's ``approach`` as graph/v12 carries it (R4), in the record's
    order, ``None`` on a product rendered before it; one per route ``_hole_nodes`` answers."""
    row = rows[node_id]
    return [_text_or_none(d.get("approach")) for d in row.get("decompositions") or []]


def _hole_nodes(
    node_id: str, rows: Mapping[str, Mapping[str, Any]]
) -> list[tuple[str, list[tuple[str, str | None]]]]:
    """Each route of ``node_id`` as ``(partial, [(hole name, node or None)])``, with F27-R2's
    assignment of unnamed holes applied where it is unambiguous. ``closing.links`` reads it too."""
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
    holes: Sequence[tuple[str, str | None]],
    rows: Mapping[str, Mapping[str, Any]],
    entries: Mapping[str, Mapping[str, Any]],
    approach: str | None = None,
) -> Route:
    made: list[Hole] = []
    for name, nid in holes:
        row = rows.get(nid) if nid else None
        entry = entries.get(nid) if nid else None
        made.append(
            Hole(
                name=name,
                node=nid,
                # F29-R8: the label graph/v12 publishes for the hole's node (R3); None before it
                label=_text_or_none(row.get("label")) if row is not None else None,
                status=str(row.get("status")) if row is not None else None,
                attempts=int(entry.get("attempts") or 0) if entry is not None else None,
                refuted_route_classes=tuple(
                    str(c) for c in (entry.get("refuted_route_classes") or [])
                )
                if entry is not None
                else (),
                ready_since=entry.get("ready_since") if entry is not None else None,
                routes=len(row.get("decompositions") or []) if row is not None else 0,
                shelved=_shelved(row) is not None,
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
    return Route(
        f"{node_id}@{k}",
        node_id,
        partial,
        tuple(made),
        summary,
        approach,
        retired=_retired(node_id, [nid for _, nid in holes], rows),
    )


# --- following a proof (F27-R13) ---------------------------------------------------------------


@dataclass(frozen=True)
class Followed:
    """What a proved statement's proof rests on, as the page draws it beneath the statement:
    ``nodes``, every node its term rests on, transitively (sorted, the statement itself left
    out); ``routes``, the routes the proofs went through — a route of a followed node every
    hole of which is among what that node's proof used, so the proof is the route's assembly
    — in the order met; and ``lines``, each ``(used, user)`` pair a followed route does not
    already carry, so a proof that went past a route (it used one hole as a lemma, not the
    assembly) is drawn as the direct line it is."""

    nodes: tuple[str, ...]
    routes: tuple[str, ...]
    lines: tuple[tuple[str, str], ...]


def rests_on(row: Mapping[str, Any]) -> tuple[str, ...]:
    """What a node's first merged proof rests on, as ``graph.json`` publishes it: the nodes its
    term ``used`` (F18-R2) where the gate measured them, else — an older merge, ``used: null``
    — everything it could rest on: its deps, its uses and its lemmas (``NodeFacts.rests_on``,
    which the products' closure follows the same way)."""
    proofs = row.get("proofs") or []
    first = proofs[0] if proofs and isinstance(proofs[0], Mapping) else None
    used = first.get("used") if first is not None else None
    if used is not None:
        return tuple(dict.fromkeys(str(u) for u in used))
    return tuple(
        dict.fromkeys(
            [
                *(str(d) for d in row.get("deps") or []),
                *(str(u) for u in row.get("uses") or []),
                *(str(lm.get("node")) for lm in row.get("lemmas") or [] if isinstance(lm, Mapping)),
            ]
        )
    )


def _followed(
    node_id: str,
    rows: Mapping[str, Mapping[str, Any]],
    routes_by_node: Mapping[str, Sequence[Route]],
) -> Followed:
    """``Followed`` for ``node_id``: the walk of ``products.proof_closure`` over the published
    rows, each node seen once (a hand-made product may cite in a circle), unknown ids skipped."""
    seen = {node_id}
    nodes: list[str] = []
    followed_routes: list[str] = []
    lines: list[tuple[str, str]] = []
    stack = [node_id]
    while stack:
        current = stack.pop(0)
        rests = [r for r in rests_on(rows[current]) if r in rows]
        carried: set[str] = set()
        for route in routes_by_node.get(current, ()):
            holes = [str(h.node) for h in route.holes if h.node is not None]
            if route.resolved and holes and all(h in rests for h in holes):
                followed_routes.append(route.id)
                carried.update(holes)
        lines.extend((r, current) for r in rests if r not in carried)
        for r in rests:
            if r not in seen:
                seen.add(r)
                nodes.append(r)
                stack.append(r)
    return Followed(tuple(sorted(nodes)), tuple(followed_routes), tuple(sorted(lines)))


def followed(result: Routes, graph: Mapping[str, Any], node_id: str) -> Followed:
    """R13: what the proof of ``node_id`` rests on, over ``result``'s routes and ``graph``'s
    rows — the one walk the enumeration (``at_proved: follow``) and the page share."""
    rows = _rows(graph)
    if node_id not in rows:
        return Followed((), (), ())
    by_node: dict[str, list[Route]] = {}
    for r in result.routes:
        by_node.setdefault(r.node, []).append(r)
    return _followed(node_id, rows, by_node)


# --- the enumeration ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Option:
    """One way to close a node: the statements taken (proved or open), the nodes assembled on the
    way, the routes used (the outermost first) and the resolves variant gone through, if any.
    ``beneath`` and ``proof_routes`` (R13) are what following its proved members' proofs adds —
    never part of ``key``, so the option is the same option whichever way it was read."""

    members: frozenset[str]
    assemblies: tuple[str, ...] = ()
    routes: tuple[str, ...] = ()
    variant: str | None = None
    beneath: frozenset[str] = frozenset()
    proof_routes: tuple[str, ...] = ()

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
    at_proved: str = "stop"
    truncated: bool = False
    memo: dict[str, list[_Option]] = field(default_factory=dict)
    follows: dict[str, Followed] = field(default_factory=dict)

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
                beneath=frozenset().union(*(o.beneath for o in combo)),
                proof_routes=_ordered(*(o.proof_routes for o in combo)),
            )

    def proved(self, node_id: str) -> _Option:
        """A proved statement as a closed member (R5), and with ``follow`` what its proof rests
        on beneath it (R13); the walk is remembered per statement."""
        if self.at_proved != "follow":
            return _Option(frozenset([node_id]))
        if node_id not in self.follows:
            self.follows[node_id] = _followed(node_id, self.rows, self.routes_by_node)
        f = self.follows[node_id]
        return _Option(frozenset([node_id]), beneath=frozenset(f.nodes), proof_routes=f.routes)

    def bounded(self, options: Iterable[_Option], cap: int | None = None) -> list[_Option]:
        """The minimal options, deduplicated, and no more than the cap; past it the enumeration
        says it was cut. F27-T6: dominated options are dropped here, at every node, before the
        cap is applied: an option whose open statements strictly contain another's stays
        dominated under any union with the same other parts, so dropping it early loses no
        minimal set, and the cap then counts minimal sets rather than the combinations met on the
        way (live erdos-1094, 2026-10-15: 293 minimal coarser sets, cut to 58 before this).
        ``cap`` (F27-T11): a smaller cap than the enumeration's, the room left for the second
        side once the first has been counted."""
        cap = self.max_sets if cap is None else cap
        out: dict[tuple[frozenset[str], frozenset[str]], _Option] = {}
        ceiling = cap * RAW_FACTOR
        for o in options:
            if len(out) >= ceiling:
                self.truncated = True
                break
            out.setdefault(o.key(), o)
        # F27-T7 (the owner, 2026-10-15): the finest cuts keep every full expansion, one per
        # choice of routes, even one that needs strictly more than another; only the coarser cuts,
        # which number in the hundreds, keep the minimal ones alone.
        kept = _minimal(list(out.values()), self.rows) if self.cut == "any" else list(out.values())
        if len(kept) > cap:
            self.truncated = True
            kept = kept[:cap]
        return kept

    def close(self, node_id: str, path: frozenset[str]) -> tuple[list[_Option], bool]:
        """Every way to close ``node_id``, and whether a cycle was cut on the way (an answer that
        cut a cycle depends on the path and is not remembered)."""
        if node_id not in self.rows:
            return [], False
        status = self.status(node_id)
        if status == PROVED:
            return [self.proved(node_id)], False
        # F31-R4 (D-14, D-25 v3.47): a shelved open statement is work the frontier refuses, so no
        # set rests on it, as none rests on a dead one; a shelved *proved* one returned above (Q6).
        if status in DEAD_STATUSES or _shelved(self.rows[node_id]) is not None:
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
                    o.beneath,
                    o.proof_routes,
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
    at_proved: str = "stop",
) -> Routes:
    """A target's routes and sufficient sets from its ``graph.json`` and its frontier entries.
    ``at_proved`` (R13): ``stop`` ends a cut at a proved statement; ``follow`` also lists what
    its proof rests on."""
    if cut not in CUTS:
        msg = f"unknown cut {cut!r}: expected one of {', '.join(CUTS)}"
        raise ValueError(msg)
    if at_proved not in AT_PROVED:
        msg = f"unknown at_proved {at_proved!r}: expected one of {', '.join(AT_PROVED)}"
        raise ValueError(msg)
    rows = _rows(graph)
    target_id = str(graph.get("target_id"))
    root = str(graph.get("root"))
    entries = _entries(frontier_entries, target_id)
    by_node: dict[str, list[Route]] = {}
    for node_id in rows:
        approaches = _approaches(node_id, rows)
        for k, (partial, holes) in enumerate(_hole_nodes(node_id, rows), start=1):
            by_node.setdefault(node_id, []).append(
                _route_of(
                    node_id,
                    k=k,
                    partial=partial,
                    holes=holes,
                    rows=rows,
                    entries=entries,
                    approach=approaches[k - 1],
                )
            )
    # The record's order: the products list nodes sorted, and each node's routes in merge order.
    all_routes = tuple(r for node_id in rows for r in by_node.get(node_id, ()))
    walker = _Enumerator(rows, by_node, cut, max(1, max_sets), at_proved)
    proving: list[_Option] = []
    refuting: list[_Option] = []
    if root in rows:
        status = walker.status(root)
        proving, _ = walker.close(root, frozenset())
        # A refuted root (D-12 #2) is settled: its resolves variants close nothing now, as a
        # proved root's close nothing more.
        if status not in (PROVED, "refuted"):
            proving.extend(_via(walker, rows, root, RESOLVES))
        # D-25 v3.46: the other side — each refutes variant (D-30 v3.46) closed exactly as a
        # resolves one is — while the root is neither proved (nothing to refute) nor dead.
        if status != PROVED and status not in DEAD_STATUSES:
            refuting = _via(walker, rows, root, REFUTES)
    # Domination (cut: any) is judged within a side: a refuting set is never dropped for a
    # proving set it contains, or the other way round. The cap is overall, the proving sets
    # first: the refuting side gets the room the proving side left.
    kept_proving = walker.bounded(proving)
    kept_refuting = (
        walker.bounded(refuting, cap=walker.max_sets - len(kept_proving)) if refuting else []
    )
    minimal = [(o, PROVES) for o in kept_proving] + [(o, REFUTES) for o in kept_refuting]
    # R13: a set's statements are its members and, when followed, what their proofs rest on;
    # its id is its members' alone, so a set has one id whichever way it was read.
    listed = {id(o): o.members | o.beneath for o, _ in minimal}
    held: dict[str, int] = {}  # across both sides: a statement may serve either (D-25 v3.46)
    for o, _ in minimal:
        for m in listed[id(o)]:
            held[m] = held.get(m, 0) + 1
    sets = tuple(
        SufficientSet(
            id=_set_id(o),
            statements=tuple(sorted(listed[id(o)])),
            proved=tuple(sorted(m for m in listed[id(o)] if str(rows[m].get("status")) == PROVED)),
            open=tuple(sorted(m for m in listed[id(o)] if str(rows[m].get("status")) != PROVED)),
            assemblies=o.assemblies,
            routes=o.routes,
            variant=o.variant,
            shared=sum(1 for m in listed[id(o)] if held[m] > 1),
            proof_routes=o.proof_routes,
            settles=settles,
        )
        for o, settles in minimal
    )
    return Routes(target_id, root, cut, walker.truncated, all_routes, sets, at_proved)


def _via(
    walker: _Enumerator, rows: Mapping[str, Mapping[str, Any]], root: str, relation: str
) -> list[_Option]:
    """Every way to close each variant of the root carrying ``relation``, in the rows' order,
    each option tagged with the variant it goes through (D-30: a dead or superseded variant
    closes nothing, which ``close`` already answers)."""
    out: list[_Option] = []
    for vid, row in rows.items():
        if vid == root or row.get("relation") != relation:
            continue
        via, _ = walker.close(vid, frozenset())
        out.extend(replace(o, variant=o.variant or vid) for o in via)
    return out


# --- the selector tree (F29-R6; D-25 v3.44) ----------------------------------------------------


@dataclass(frozen=True)
class Selector:
    """One node of the selector tree over a target's sufficient sets. A leaf (``set`` set) is one
    published set; an interior node is the family of sets that share every choice above it,
    split on ``node``, the next statement on which they choose different routes, one child per
    route in the record's order. ``sets`` counts the leaves beneath. Built from the enumerated
    sets alone, never from the graph (F29-Q1): a hole shared between branches makes the
    unrolled OR tree over-count, and the sets already know."""

    route: str | None  # the route this branch chose, None at the top
    node: str | None  # the statement the children choose on, None at a leaf
    set: str | None  # the one set a leaf is
    sets: int
    children: tuple[Selector, ...] = ()
    #: D-25 v3.46 (F27-T11): the side this family settles, on the two children of the fork the
    #: tree opens on when sets of both sides exist (``proves`` first, then ``refutes``); None
    #: everywhere else, and everywhere when one side only.
    side: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "node": self.node,
            "set": self.set,
            "sets": self.sets,
            "side": self.side,
            "children": [c.as_dict() for c in self.children],
        }


def _choice_at(s: SufficientSet, node_id: str) -> str | None:
    return next((r for r in s.routes if r.rsplit("@", 1)[0] == node_id), None)


def _split(members: Sequence[SufficientSet], route: str | None) -> Selector:
    if len(members) == 1:
        return Selector(route, None, members[0].id, 1)
    # The first statement, in the order the record gives the routes of the first member, on
    # which the family does not all choose alike; a set that passes through no route of that
    # statement at all (it is proved on that set's path, or taken directly) is its own branch.
    for rid in members[0].routes:
        node_id = rid.rsplit("@", 1)[0]
        choices = [_choice_at(s, node_id) for s in members]
        if len(set(choices)) < 2:
            continue
        groups: dict[str | None, list[SufficientSet]] = {}
        for s, c in zip(members, choices, strict=True):
            groups.setdefault(c, []).append(s)
        children = tuple(_split(g, c) for c, g in groups.items())
        return Selector(route, node_id, None, len(members), children)
    # Members that differ in no route choice (several sets through the same routes: a variant,
    # or the same open statements reached two ways): list each as a leaf of this family.
    return Selector(
        route, None, None, len(members), tuple(Selector(None, None, s.id, 1) for s in members)
    )


def selector_tree(result: Routes) -> Selector:
    """The selector tree of ``result``'s sets (F29-R6). Every leaf is one set and every set one
    leaf, in the record's order; ``sets`` on the top node is the number of sets. D-25 v3.46:
    when sets of both sides exist the tree opens on a fork — a top node that splits on no
    statement, with two children, the proving family then the refuting one, each carrying its
    ``side`` and being the split of its own sets alone; with one side only there is no fork."""
    if not result.sets:
        return Selector(None, None, None, 0)
    by_side = {side: [s for s in result.sets if s.settles == side] for side in SIDES}
    if all(by_side.values()):
        children = tuple(replace(_split(by_side[side], None), side=side) for side in SIDES)
        return Selector(None, None, None, len(result.sets), children)
    return _split(list(result.sets), None)
