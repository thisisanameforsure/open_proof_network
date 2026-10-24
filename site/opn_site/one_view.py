"""F30: one statement graph (the owner's request of 2026-10-18).

The problem page's two drawings become one. The merged graph is every statement of ``graph.json``
plus one junction per route reachable from the root (F27's ``drawn``), a statement's hole
dependencies rerouted through its junctions. A *view* is a subset of that graph with the lines
between its members:

* ``all`` — everything; ``routes`` — the statements on a way to close the root and their
  junctions (the layout the page opens on, R4);
* one per node of the selector tree (``routes.selector_tree``, F29-R6): the union of the sets
  beneath it (statements, assemblies, variant, junctions of the routes they use); a leaf is one
  set;
* one per selector edge: the *segment* the edge commits to (R6, Q3) — what every set beneath the
  child shares, lying under the statement the edge is a route of, through that route, down to and
  including the child's split statement; the trunk edge runs from the root to the top split;
* one per proof of the target (Q4): its closure and the edges its term follows.

Every view is laid out by ``dag.layout`` seeded with the ``all`` layout's order (Q2), so
statements two views share keep their left-to-right order (R10) and a transition slides little.
Keys: ``all``, ``routes``, ``sel`` (the top), ``sel/<route>/...`` (a child per route chosen,
``direct`` where a family takes the statement directly, ``set:<id>`` for a leaf a family lists
without a choice), ``edge/<child key>``, ``proof/<k>``; and, F27-R13, ``follow/<key>`` for every
selector node, leaf and edge: the same view read with ``at_proved: follow``, so beneath each
proved statement it also holds what that statement's proof rests on, the routes the proof went
through and the direct lines it took (``routes.followed``). The selector is built from the
plain keys alone; the page's toggle swaps a view for its twin.
"""

from __future__ import annotations

import json
import textwrap
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from html import escape
from typing import Any

from opn_gate import closing, routes
from opn_site import dag, routes_view

#: A junction is a dot in a box this wide (as the routes drawing drew it, F27-T3).
JUNCTION_W = routes_view.JUNCTION_W
ALL = "all"
ROUTES = "routes"
#: F30-T11: the band's own view (never in the layouts JSON: the script does not move it).
BAND = "band"
TOP = "sel"
EDGE = "edge/"
PROOF = "proof/"
DIRECT = "direct"
#: F27-R13: the prefix of a set view's followed twin.
FOLLOW = "follow/"


@dataclass(frozen=True)
class View:
    """One state of the drawing: its nodes (statements and junctions), the lines between them
    as ``dag.Line`` (lower, upper, kind), the sets it stands for (none for ``all``, ``routes``
    and a proof), and for a selector node or edge what it says: the route chosen (``route``),
    the statement the node splits on (``split``), a leaf's set number or a proof's index from
    zero (``index``)."""

    key: str
    kind: str
    nodes: tuple[str, ...]
    lines: tuple[dag.Line, ...]
    sets: tuple[str, ...] = ()
    route: str | None = None
    split: str | None = None
    index: int = 0
    parent: str | None = None
    #: F04-T55 (D-25 v3.46): the side of the top fork this view lies under (``proves`` or
    #: ``refutes``), ``None`` above the fork or when the target has one side only.
    side: str | None = None


def merged_nodes(
    graph_nodes: Iterable[Mapping[str, Any]], d: routes_view.Drawn, root: str | None = None
) -> dict[str, dict[str, Any]]:
    """The layout's node dicts keyed by id: each statement with the hole dependencies of its
    drawn routes rerouted through those routes' junctions (its ``deps`` and ``uses`` lose the
    holes and its ``deps`` gain the junction ids), and one dict per junction whose ``deps`` are
    its holes; with ``root``, the root's ``relations`` (its drawn variants, F04-T55). Everything
    else a row carries (``lemmas``, ``proposed_for``, the status) stays."""
    out: dict[str, dict[str, Any]] = {}
    by_node: dict[str, list[str]] = {}
    for rid, r in d.junctions.items():
        by_node.setdefault(r.node, []).append(rid)
    for n in graph_nodes:
        nid = str(n["node_id"])
        row = dict(n)
        mine = by_node.get(nid, [])
        held = {h for rid in mine for h in d.below.get(rid, [])}
        row["deps"] = [str(x) for x in n.get("deps") or [] if str(x) not in held] + mine
        if n.get("uses"):
            row["uses"] = [str(u) for u in n["uses"] if str(u) not in held]
        out[nid] = row
    for rid in d.junctions:
        out[rid] = {"node_id": rid, "status": "route", "deps": list(d.below.get(rid, []))}
    # F04-T55 (D-30 v3.46): the variants ``drawn`` put below the root are its relation trunks,
    # each with its label, which ``dag.lines`` draws as ``edge relation <label>``.
    if root is not None and root in out:
        trunks = {
            v: str(out[v]["relation"])
            for v in d.below.get(root, [])
            if v in out
            and v not in d.junctions
            and out[v].get("relation") in routes_view.TRUNK_LABELS
            and v not in [str(x) for x in out[root]["deps"]]
        }
        if trunks:
            out[root]["relations"] = trunks
    return out


def band_ids(rows: Sequence[Mapping[str, Any]], d: routes_view.Drawn) -> tuple[str, ...]:
    """F30-T11: the band's nodes — ``dag.band_of`` plus the junctions of their routes."""
    band = dag.band_of(rows, d.statements)  # F30-T16: what the root's walk reached is the tree's
    held = set(band)
    return (*band, *(rid for rid, r in d.junctions.items() if r.node in held))


def shelved_ids(merged: Mapping[str, Mapping[str, Any]], d: routes_view.Drawn) -> set[str]:
    """F31-T10: the statements whose row carries ``shelved`` (``graph/v15``); never a junction."""
    return {i for i, r in merged.items() if i not in d.junctions and r.get("shelved")}


def shelving_words(
    r: routes.Route, rows: Mapping[str, Mapping[str, Any]], holes: Sequence[str]
) -> str | None:
    """F31-T10 (R7): what shelving does to a route, for its junction's title — ``None`` when
    nothing is shelved, or when only proved holes are (Q6: the route stays live). Every hole
    shelved through the route's own record is a retirement; every hole shelved otherwise is
    said so; one shelved unproved hole kills the route (F31-R4)."""
    facts = {h: rows[h].get("shelved") for h in holes if h in rows}
    shelved = {h: f for h, f in facts.items() if isinstance(f, Mapping) and f}
    if not shelved:
        return None
    if len(shelved) == len(facts):
        retired = all(
            f.get("scope") == "route" and f.get("via") == r.node for f in shelved.values()
        )
        first = next(iter(shelved.values()))
        head = "retired" if retired else "every hole shelved"
        return f"{head} by {first.get('by')} on {first.get('date')}: {first.get('cause')}"
    if any(str(rows[h].get("status")) != routes.PROVED for h in shelved):
        return "closes nothing (a hole is shelved and unproved)"
    return None


def _subset(merged: Mapping[str, Mapping[str, Any]], ids: Iterable[str]) -> list[dict[str, Any]]:
    keep = [i for i in dict.fromkeys(ids) if i in merged]
    return [dict(merged[i]) for i in keep]


def _lines(
    rows: Sequence[dict[str, Any]], extra: Iterable[tuple[str, str]] = ()
) -> tuple[dag.Line, ...]:
    """The lines among ``rows`` (``dag.lines``) and, F27-R13, the direct lines a followed proof
    took that the merged rows do not draw (a hole used as a lemma rather than through its
    route), each once, both ends in the view."""
    ids = {str(r["node_id"]) for r in rows}
    out = list(dag.lines(list(rows)))
    drawn = {(src, dst) for src, dst, _k in out}
    for src, dst in extra:
        if src in ids and dst in ids and (src, dst) not in drawn:
            out.append((src, dst, "edge"))
            drawn.add((src, dst))
    return tuple(out)


def _view(
    key: str,
    kind: str,
    merged: Mapping[str, Mapping[str, Any]],
    ids: Iterable[str],
    extra: Iterable[tuple[str, str]] = (),
    **facts: Any,
) -> View:
    rows = _subset(merged, ids)
    return View(key, kind, tuple(r["node_id"] for r in rows), _lines(rows, extra), **facts)


def _on(s: routes.SufficientSet, root: str, d: routes_view.Drawn) -> set[str]:
    """What a set lights (F27's ``lit_sets``): the root, its statements, assemblies, variant,
    and the junctions of the routes it uses — and, when read with ``at_proved: follow``, of the
    routes its proved statements' proofs went through (``proof_routes``, F27-R13)."""
    on = {root, *s.statements, *s.assemblies}
    if s.variant:
        on.add(s.variant)
    on.update(rid for rid in (*s.routes, *s.proof_routes) if rid in d.junctions)
    return on


def _leaves(sel: routes.Selector) -> tuple[str, ...]:
    if sel.set is not None:
        return (sel.set,)
    return tuple(sid for c in sel.children for sid in _leaves(c))


def _segment(
    start: str,
    through: str | None,
    stop: str | None,
    common: set[str],
    d: routes_view.Drawn,
) -> list[str]:
    """The committed part: ``start`` and what lies beneath it through ``through`` (a junction, or
    ``None`` to take ``start`` directly) over the nodes in ``common``, not expanding ``stop``."""
    out = [start]
    if through is None or through not in common:
        return out
    stack = [through]
    seen = {start}
    while stack:
        v = stack.pop()
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
        if v == stop:
            continue
        stack.extend(x for x in d.below.get(v, []) if x in common and x not in seen)
    return out


def views(
    graph: Mapping[str, Any],
    result: routes.Routes,
    *,
    proofs: Sequence[dag.ProofMarks] = (),
    follow: routes.Routes | None = None,
) -> dict[str, View]:
    """Every view of a target, keyed (see the module), the selector's in depth-first order.
    ``follow`` (F27-R13), the same target read with ``at_proved: follow``, adds a ``follow/``
    twin of every set view."""
    d = routes_view.drawn(graph, result)
    rows = [n for n in graph.get("nodes") or [] if isinstance(n, Mapping)]
    root = result.root
    merged = merged_nodes(rows, d, root)
    # F30-T11: the band's statements and the junctions of their routes are in no view but
    # the band's own; the toggle counts them in nothing (R4).
    band = band_ids(rows, d)
    out: dict[str, View] = {}
    # F30-T16: a superseded statement is in no view (the owner: "do not need to be visible").
    gone = {i for i, r in merged.items() if str(r.get("status")) == "superseded"}
    # F31-T10 (R7, Q2): a shelved statement, proved or not, leaves ``routes`` and stays in
    # ``all`` (the order seed, F30-Q2); a route every hole of which is shelved (retired, or
    # shelved one by one) draws no junction there either. A set keeps a shelved member only
    # when it is proved (Q6: a kernel-checked proof is a fact), drawn dim; a route with a
    # shelved unproved hole is dead, so its junction leaves the set views too.
    shelved = shelved_ids(merged, d)
    cut = {
        rid for rid in d.junctions if d.below.get(rid) and all(h in shelved for h in d.below[rid])
    }
    dim = {i for i in shelved if str(merged[i].get("status")) != routes.PROVED}
    dead = {rid for rid in d.junctions if any(h in dim for h in d.below.get(rid, []))}
    out[ALL] = _view(ALL, ALL, merged, [i for i in merged if i not in band and i not in gone])
    out[ROUTES] = _view(
        ROUTES,
        ROUTES,
        merged,
        [
            i
            for i in (*d.statements, *d.junctions)
            if i not in band and i not in shelved and i not in cut
        ]
        or [root],
    )
    if band:
        out[BAND] = _view(BAND, BAND, merged, band)
    out.update(_set_views(graph, result, d, merged, prefix=""))
    if follow is not None:
        out.update(_set_views(graph, follow, d, merged, prefix=FOLLOW))
    if band:
        # A followed proof may rest on a band statement (F27-R13): it stays in the column and
        # the use is its lit line, so no view draws it twice (F30-T16: one place, not two).
        held = set(band)
        for key, v in list(out.items()):
            if key != BAND and held & set(v.nodes):
                out[key] = replace(
                    v,
                    nodes=tuple(n for n in v.nodes if n not in held),
                    lines=tuple(ln for ln in v.lines if ln[0] not in held and ln[1] not in held),
                )
    if gone:
        # F30-T16: and no other view draws one either.
        for key, v in list(out.items()):
            if gone & set(v.nodes):
                out[key] = replace(
                    v,
                    nodes=tuple(n for n in v.nodes if n not in gone),
                    lines=tuple(ln for ln in v.lines if ln[0] not in gone and ln[1] not in gone),
                )
    # F31-T10 (Q6): the set views lose the shelved unproved statements and the routes they
    # kill; ``all`` and the band keep them, and ``routes`` keeps a dead junction, drawn dead.
    _drop_from(out, dim | dead, keep=(ALL, ROUTES, BAND))
    for k, m in enumerate(proofs):
        ids = sorted(m.nodes)
        by_dst: dict[str, list[str]] = {}
        for src, dst in sorted(m.edges):
            by_dst.setdefault(dst, []).append(src)
        prows = [
            {
                "node_id": i,
                "status": str(merged.get(i, {}).get("status", "proved")),
                "deps": by_dst.get(i, []),
            }
            for i in ids
        ]
        out[f"{PROOF}{k}"] = View(
            f"{PROOF}{k}", "proof", tuple(ids), tuple(dag.lines(prows)), index=k
        )
    return out


def _drop_from(out: dict[str, View], drop: set[str], *, keep: Sequence[str]) -> None:
    """Take ``drop``'s nodes, and every line touching one, out of every view but ``keep``."""
    if not drop:
        return
    for key, v in list(out.items()):
        if key in keep or not drop & set(v.nodes):
            continue
        out[key] = replace(
            v,
            nodes=tuple(n for n in v.nodes if n not in drop),
            lines=tuple(ln for ln in v.lines if ln[0] not in drop and ln[1] not in drop),
        )


def _set_views(
    graph: Mapping[str, Any],
    result: routes.Routes,
    d: routes_view.Drawn,
    merged: Mapping[str, Mapping[str, Any]],
    *,
    prefix: str,
) -> dict[str, View]:
    """The selector's views over ``result``'s sets — a node, a leaf, an edge each — keyed under
    ``prefix`` (``""`` for the published reading, ``FOLLOW`` for its twin). Under ``follow`` a
    set's proved statements carry the lines their proofs took (``routes.followed``)."""
    root = result.root
    out: dict[str, View] = {}
    index = {s.id: k for k, s in enumerate(result.sets, start=1)}
    on = {s.id: _on(s, root, d) for s in result.sets}
    taken: dict[str, tuple[tuple[str, str], ...]] = {}
    extra: dict[str, list[tuple[str, str]]] = {}
    if result.at_proved == "follow":
        for s in result.sets:
            lines: list[tuple[str, str]] = []
            for m in s.proved:
                if m not in taken:
                    taken[m] = routes.followed(result, graph, m).lines
                lines.extend(taken[m])
            extra[s.id] = lines

    def lines_of(sids: Sequence[str]) -> list[tuple[str, str]]:
        return [pair for sid in sids for pair in extra.get(sid, [])]

    def family(sel: routes.Selector) -> set[str]:
        nodes: set[str] = set()
        for sid in _leaves(sel):
            nodes |= on[sid]
        return nodes

    def common(sel: routes.Selector) -> set[str]:
        beneath = _leaves(sel)
        shared = set(on[beneath[0]])
        for sid in beneath[1:]:
            shared &= on[sid]
        return shared

    def visit(
        sel: routes.Selector,
        key: str,
        parent: str | None,
        split_on: str | None,
        side: str | None = None,
    ) -> None:
        # F04-T55 (D-25 v3.46): a child of the top fork may carry a side; every view beneath it
        # (and the edge into it) wears that side.
        side = routes_view.side_of(sel) or side
        beneath = _leaves(sel)
        if sel.set is not None:
            out[prefix + key] = _view(
                prefix + key,
                "leaf",
                merged,
                sorted(on[sel.set]),
                lines_of(beneath),
                sets=beneath,
                route=sel.route,
                split=split_on,
                index=index[sel.set],
                parent=prefix + parent if parent is not None else None,
                side=side,
            )
        else:
            out[prefix + key] = _view(
                prefix + key,
                "node",
                merged,
                sorted(family(sel)),
                lines_of(beneath),
                sets=beneath,
                route=sel.route,
                split=sel.node,
                parent=prefix + parent if parent is not None else None,
                side=side,
            )
        if split_on is not None:
            # The edge into this node: from the statement its parent split on, through the
            # route it chose (or that statement alone when taken directly), over what every
            # set beneath shares, down to and including this node's own split (Q3).
            seg = _segment(split_on, sel.route, sel.node, common(sel), d)
            out[prefix + EDGE + key] = View(
                prefix + EDGE + key,
                "edge",
                tuple(seg),
                _lines(_subset(merged, seg), lines_of(beneath)),
                sets=beneath,
                route=sel.route,
                split=split_on,
                parent=prefix + key,
                side=side,
            )
        for c in sel.children:
            if routes_view.side_of(c) is not None:
                part = str(routes_view.side_of(c))
            elif c.route is not None:
                part = c.route
            elif c.set is not None and sel.node is None:
                part = f"set:{c.set}"
            else:
                part = DIRECT
            visit(c, f"{key}/{part}", key, sel.node, side)

    tree = routes.selector_tree(result)
    if tree.sets:
        visit(tree, TOP, None, None)
        if tree.node is not None and tree.node != root:
            # The trunk: root down to the first split, common to every set.
            shared = common(tree)
            first = next((rid for rid in d.below.get(root, []) if rid in shared), None)
            seg = _segment(root, first, tree.node, shared, d)
            out[prefix + EDGE + TOP] = View(
                prefix + EDGE + TOP,
                "edge",
                tuple(seg),
                _lines(_subset(merged, seg), lines_of(_leaves(tree))),
                sets=_leaves(tree),
                split=root,
                parent=prefix + TOP,
            )
    return out


def _rows_for(view: View, status: Mapping[str, str]) -> list[dict[str, Any]]:
    """The dicts ``dag.layout`` reads for a view: its nodes with exactly its lines, each under
    the key its kind came from, so the layout draws the view's lines and no others."""
    rows: dict[str, dict[str, Any]] = {
        i: {"node_id": i, "status": status.get(i, "route"), "deps": [], "uses": [], "lemmas": []}
        for i in view.nodes
    }
    for src, dst, kind in view.lines:
        if kind == "edge use":
            rows[dst]["uses"].append(src)
        elif kind == "edge lemma":
            rows[dst]["lemmas"].append({"node": src})
        elif kind.startswith(dag.RELATION_KIND + " "):  # F04-T55: a variant's trunk
            rows[dst].setdefault("relations", {})[src] = kind[len(dag.RELATION_KIND) + 1 :]
        else:
            rows[dst]["deps"].append(src)
    return list(rows.values())


def order_seed(lay: dag.Layout) -> dict[str, float]:
    """Q2: the seed every other view is laid out from — the centre of each node in ``lay``."""
    return {p.node_id: p.x + p.w / 2 for p in lay.placed}


def layout_view(  # noqa: PLR0913 — the layout's inputs, one view at a time
    view: View,
    status: Mapping[str, str],
    *,
    root: str,
    prefix: str | None,
    widths: dag.Widths,
    labels: dag.Labels,
    order: Mapping[str, float] | None,
    apart: bool = True,
) -> dag.Layout:
    return dag.layout(
        _rows_for(view, status),
        root=root if root in view.nodes else None,
        prefix=prefix,
        widths=widths,
        labels=labels,
        order=order,
        apart=apart,
    )


def layouts(
    graph_nodes: Iterable[Mapping[str, Any]],
    vs: Mapping[str, View],
    *,
    root: str,
    prefix: str | None = None,
    labels: dag.Labels = None,
) -> dict[str, dag.Layout]:
    """One ``dag.Layout`` per view; ``all`` first and unseeded, every other seeded with the
    centre of each node in ``all`` (Q2). A junction (an id no row has) is a dot-wide box. The
    band (F30-T11) is laid out with nothing set aside: a lone crux is a row, not a group."""
    status = statuses(graph_nodes)
    widths = junction_widths(vs[ALL], status)
    if BAND in vs:
        widths.update(junction_widths(vs[BAND], status))
    out: dict[str, dag.Layout] = {}
    seed: dict[str, float] | None = None
    for key, v in vs.items():
        lay = layout_view(
            v,
            status,
            root=root,
            prefix=prefix,
            widths=widths,
            labels=labels,
            order=seed,
            apart=key != BAND,
        )
        out[key] = lay
        if key == ALL:
            seed = order_seed(lay)
    return out


def statuses(graph_nodes: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    return {str(n["node_id"]): str(n["status"]) for n in graph_nodes if isinstance(n, Mapping)}


def junction_widths(all_view: View, status: Mapping[str, str]) -> dict[str, int]:
    return {nid: JUNCTION_W for nid in all_view.nodes if nid not in status}


def layouts_document(lays: Mapping[str, dag.Layout]) -> dict[str, Any]:
    """R6: the JSON the page embeds — per view the drawing's size, each node's ``[x, y, w]`` and
    each line's bend points; ids and numbers only. The band (F30-T11) is not a view the script
    moves to, so it is not here."""
    return {
        key: {
            "w": lay.width,
            "h": lay.height,
            "group_y": lay.group_y,
            "nodes": {p.node_id: [p.x, p.y, p.w] for p in lay.placed},
            "lines": [
                [e.src, e.dst, e.kind, [[round(x, 1), round(y, 1)] for x, y in e.points]]
                for e in lay.edges
            ],
        }
        for key, lay in lays.items()
        if key != BAND
    }


# -- the markup (T2) ----------------------------------------------------------------------------

#: The selector's edge labels are cut here; the full approach is in the edge's ``<title>``.
APPROACH_MAX = 40
SEL_PREFIX = "sel"


@dataclass(frozen=True)
class RouteRow:
    """F31-T11 (R8): one drawn route as the problem page lists it beside the sets table —
    its id (``<node>@<k>``), the statement it decomposes, the partial's file (what a retirement
    names, ``shelving/v1`` ``route``), its approach, and what shelving did to it (``None`` when
    nothing; see ``shelving_words``)."""

    id: str
    node: str
    partial: str
    approach: str | None
    shelving: str | None
    #: Every hole of it is shelved (retired, or shelved one by one): nothing is left to retire.
    cut: bool = False


@dataclass(frozen=True)
class Drawing:
    """What the page embeds (the contract is the session note of 2026-10-18): the merged
    drawing, the selector with the proof notes, the sets table, the layouts as a
    (``marks``: ``route-and``, ``route-or``, ``route-dead``, ``closable``)."""

    svg: str
    selector: str
    table: str
    layouts_json: str
    toggle: str
    marks: frozenset[str]
    sets: int
    hidden: int
    #: F27-R13: the "Stop at proved statements" toggle for the selector panel (``""`` without
    #: a selector); rendered hidden, since only the script can act on it.
    follow_toggle: str = ""
    #: F30-T11: the band of proposed statements (D-14 v3.26 as amended), its own drawing under
    #: the main one, with the overlay that carries its lines into the tree; ``""`` without one.
    band: str = ""
    #: F31-T10 (R7): how many of ``hidden`` are shelved statements (the rest are on no route).
    shelved: int = 0
    #: F31-T11 (R8): the drawn routes (the tree's, not the band's), in the drawing's order.
    routes: tuple[RouteRow, ...] = ()


def _line_key(src: str, dst: str) -> str:
    return f"{src}>{dst}"


def _status_of(rows: Mapping[str, Mapping[str, Any]], nid: str) -> str:
    return str(rows[nid].get("status")) if nid in rows else "route"


def _junction_markup(
    r: routes.Route, x: int, y: int, hidden: bool, shelving: str | None = None
) -> str:
    """One junction. ``shelving`` (F31-T10) is what shelving did to the route, when anything:
    a retired or shelved-through route is drawn dead and says so in its title."""
    holes = r.summary.holes
    live = r.live and shelving is None
    if shelving is not None:
        words = f"route {r.id}: {shelving}"
    elif r.live:
        words = f"route {r.id}: {holes} hole{'' if holes == 1 else 's'}, all needed"
    else:
        words = (
            f"route {r.id}: closes nothing (a hole is refuted, defective, abandoned, "
            "superseded or not traced)"
        )
    cx, cy = JUNCTION_W // 2, dag.NODE_H // 2
    mark = (
        f'<circle class="and-mark" cx="{cx}" cy="{cy}" r="5"/>'
        if live
        else f'<circle class="dead-mark" cx="{cx}" cy="{cy}" r="5"/>'
        f'<path class="dead-cross" d="M{cx - 3} {cy - 3}l6 6m0 -6l-6 6"/>'
    )
    off = " off-view" if hidden else ""
    return (
        f'<g class="junction {"live" if live else "dead"}{off}" data-route="{escape(r.id)}" '
        f'data-node="{escape(r.id)}" data-w="{JUNCTION_W}" transform="translate({x},{y})">'
        f"<title>{escape(words)}; from {escape(r.partial)}</title> "
        f'<path class="stem" d="M{cx} 0V{dag.NODE_H}"/>{mark}</g>'
    )


def _pill_markup(  # noqa: PLR0913 — one pill, every mark it may carry
    nid: str,
    p: dag.Placed,
    *,
    status: str,
    label: str,
    title: str,
    href: str,
    hidden: bool,
    proved: bool,
    closable: bool,
    or_mark: bool,
    outline: int,
    literature: dag.LitMark | None = None,
    lines: Sequence[str] | None = None,
    shelved: bool = False,
) -> str:
    """One pill. ``lines`` (F30-T14, the column of proposed statements) is the label broken to
    fit the pill's width: one line per row, the pill as tall as its lines, every mark still on
    the first line. ``shelved`` (F31-T10) adds the class the stylesheet dims; the status class
    is unchanged (shelving is a mark, not a status)."""
    height = dag.NODE_H + (len(lines) - 1) * BAND_LINE_H if lines else dag.NODE_H
    if lines and len(lines) > 1:
        text = (
            f'<text x="28" y="{dag.NODE_H // 2 + 5}">'
            + "".join(
                f'<tspan x="28" dy="{0 if i == 0 else BAND_LINE_H}">{escape(ln)}</tspan>'
                for i, ln in enumerate(lines)
            )
            + "</text> "
        )
    else:
        text = f'<text x="28" y="{dag.NODE_H // 2 + 5}">{escape(label)}</text> '
    cls = f"node status-{escape(status)}"
    if proved:
        cls += " proved"
    if closable:
        cls += " closable"
    if shelved:
        cls += " shelved"
    if hidden:
        cls += " off-view"
    diamond = (
        f'<path class="or-mark" d="M{p.w / 2:g} {dag.NODE_H - routes_view.DIAMOND}'
        f"l{routes_view.DIAMOND} {routes_view.DIAMOND}l-{routes_view.DIAMOND} "
        f'{routes_view.DIAMOND}l-{routes_view.DIAMOND} -{routes_view.DIAMOND}Z"/>'
        if or_mark
        else ""
    )
    asm = (
        f'<rect class="asm" x="12" y="{dag.NODE_H // 2 - 4}" width="8" height="8"/>'
        if closable
        else ""
    )
    return (
        f'<a href="{escape(href)}"><g class="{cls}" data-node="{escape(nid)}" '
        f'data-w="{p.w}" transform="translate({p.x},{p.y})">'
        f"<title>{escape(title)}</title> "
        f'<rect class="pill" width="{p.w}" height="{height}" rx="8"/>'
        f'<circle cx="16" cy="{dag.NODE_H // 2}" r="4"/>{asm}'
        f"{text}"
        f'<circle class="halo" cx="{p.w - 14}" cy="{dag.NODE_H // 2}" r="3"/>'
        + dag.outline_mark(outline, p.w)
        + dag.literature_mark(literature, p.w)
        + f"{diamond}</g></a>"
    )


def _dag_svg(  # noqa: PLR0913 — the whole drawing, every element once
    vs: Mapping[str, View],
    lays: Mapping[str, dag.Layout],
    d: routes_view.Drawn,
    rows: Mapping[str, Mapping[str, Any]],
    *,
    href: Mapping[str, str],
    names: dag.Prefix,
    labels: dag.Labels,
    titles: Mapping[str, str],
    outlines: Mapping[str, int],
    closable: Mapping[str, Any],
    literature: dag.Literature = None,
) -> str:
    opening = lays[ROUTES]
    shown_nodes = set(vs[ROUTES].nodes)
    shown_lines = {(s, t) for s, t, _k in vs[ROUTES].lines}
    # Every node's place: the opening layout's, else the first layout that has it.
    at: dict[str, dag.Placed] = {p.node_id: p for p in opening.placed}
    edge_at: dict[tuple[str, str], dag.Edge] = {(e.src, e.dst): e for e in opening.edges}
    for key, lay in lays.items():
        if key in (ROUTES, BAND):
            continue
        for p in lay.placed:
            at.setdefault(p.node_id, p)
        for e in lay.edges:
            edge_at.setdefault((e.src, e.dst), e)
    parts = [
        f'<svg class="dag" data-view="{ROUTES}" viewBox="0 0 {opening.width} {opening.height}" '
        f'width="{opening.width}" height="{opening.height}" role="img" '
        'aria-label="statement graph">'
    ]
    for (src, dst), e in sorted(edge_at.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        cls = e.kind
        if (src, dst) not in shown_lines:
            cls += " off-view"
        if "superseded" in (_status_of(rows, src), _status_of(rows, dst)):
            cls += " touches-superseded"
        parts.append(
            f'<path class="{cls}" data-from="{escape(src)}" data-to="{escape(dst)}" '
            f'data-key="{escape(_line_key(src, dst))}" d="{dag.path_d(e)}"/>'
        )
    # The group no line joins: drawn from the opening layout, or from the first layout that has
    # one and hidden until the script moves to it (T3's finding: the toggle's own case).
    grouped = opening if opening.loose else next((lay for lay in lays.values() if lay.loose), None)
    if grouped is not None:
        off = "" if grouped is opening else " off-view"
        parts.append(
            f'<line class="dag-divider{off}" x1="{dag.PAD}" y1="{grouped.group_y - 22}" '
            f'x2="{grouped.width - dag.PAD}" y2="{grouped.group_y - 22}"/>'
            f'<text class="dag-group{off}" x="{grouped.width // 2}" y="{grouped.group_y}">'
            f"{escape(dag.GROUP_LABEL)}</text>"
        )
    # F30-T15: a set view through a spec revised into a variant draws that spec and its holes,
    # which no resting view holds (the column does), so their pills are drawn too, off-view.
    resting = set(vs[ALL].nodes)
    extra = sorted(
        {n for k, v in vs.items() if k != BAND for n in v.nodes if n not in resting and n in at}
    )
    for nid in (*vs[ALL].nodes, *extra):
        p = at[nid]
        hidden = nid not in shown_nodes
        if nid in d.junctions:
            r = d.junctions[nid]
            words = shelving_words(r, rows, d.below.get(nid, []))  # F31-T10
            parts.append(_junction_markup(r, p.x, p.y, hidden, words))
            continue
        status = _status_of(rows, nid)
        label = dag.label_of(nid, names, labels)
        parts.append(
            _pill_markup(
                nid,
                p,
                status=status,
                label=label,
                title=titles.get(nid, f"{nid}: {status}"),
                href=href.get(nid, "#"),
                hidden=hidden,
                proved=status == routes.PROVED,
                closable=nid in closable,
                or_mark=d.alternatives.get(nid, 0) >= 2,
                outline=outlines.get(nid, 0),
                literature=(literature or {}).get(nid),
                shelved=bool(rows.get(nid, {}).get("shelved")),  # F31-T10
            )
        )
    parts.append("</svg>")
    return "\n".join(parts)


#: F30-T13: the space between two rows of the column of proposed statements.
BAND_ROW_GAP = 10
#: F30-T14 (the owner, 2026-10-22): the column is half the width its widest one-line pill would
#: need, never narrower than this, and a label too long for it wraps, one line every BAND_LINE_H.
BAND_MIN_W = 160
BAND_LINE_H = 16


def _band_svg(  # noqa: PLR0913 — the band, every element once
    vs: Mapping[str, View],
    lays: Mapping[str, dag.Layout],
    d: routes_view.Drawn,
    rows: Mapping[str, Mapping[str, Any]],
    *,
    href: Mapping[str, str],
    names: dag.Prefix,
    labels: dag.Labels,
    titles: Mapping[str, str],
    outlines: Mapping[str, int],
    closable: Mapping[str, Any],
    literature: dag.Literature = None,
    links: Sequence[dag.Line] = (),
) -> str:
    """F30-T11, F30-T13 (D-14 v3.26 as amended by v3.46; the owner, 2026-10-21): the proposed
    statements as one column at the top right of the drawing's card — its heading and one line of
    help, then every band statement (a crux and its own holes, ``dag.band_column``'s order) as a
    plain pill, right-aligned, one per row, with no line and no junction at rest; and, over the
    card, every measured line from a band statement (``links``, the band's own lines among
    them): each a ``path.band-link`` with its ends and kind and no ``d``, which the script draws
    from the pills' boxes while it is lit."""
    if BAND not in vs:
        return ""
    order = dag.band_column(
        list(rows.values()), [b for b in vs[BAND].nodes if b not in d.junctions]
    )
    widths = {pl.node_id: pl.w for pl in lays[BAND].placed}
    col = max(BAND_MIN_W, max((widths.get(nid, 0) for nid in order), default=0) // 2)
    per_line = max(8, int((col - dag.PILL_PAD) / dag.CHAR_W))
    wrapped = {
        nid: textwrap.wrap(dag.label_of(nid, names, labels), per_line, break_on_hyphens=False)
        or [dag.label_of(nid, names, labels)]
        for nid in order
    }
    tops: list[int] = []
    y = 0
    for nid in order:
        tops.append(y)
        y += dag.NODE_H + (len(wrapped[nid]) - 1) * BAND_LINE_H + BAND_ROW_GAP
    height = max(y - BAND_ROW_GAP, 0)
    parts = [
        '<div class="band-wrap"><div class="band-head">'
        f'<span class="kicker">{escape(dag.BAND_LABEL)}</span>'
        f'<p class="band-cue">{escape(dag.BAND_HELP)}</p></div><div class="band-scroll">'
        f'<svg class="dag band" viewBox="0 0 {col} {height}" width="{col}" '
        f'height="{height}" role="img" aria-label="speculative statements">'
    ]
    for i, nid in enumerate(order):
        p = dag.Placed(nid, _status_of(rows, nid), 0, 0, tops[i], col)
        status = _status_of(rows, nid)
        parts.append(
            _pill_markup(
                nid,
                p,
                status=status,
                label=dag.label_of(nid, names, labels),
                title=titles.get(nid, f"{nid}: {status}"),
                href=href.get(nid, "#"),
                hidden=False,
                proved=status == routes.PROVED,
                closable=nid in closable,
                or_mark=d.alternatives.get(nid, 0) >= 2,
                outline=outlines.get(nid, 0),
                literature=(literature or {}).get(nid),
                lines=wrapped[nid],
            )
        )
    parts.append('</svg></div><svg class="band-links" aria-hidden="true">')
    parts.extend(
        f'<path class="band-link {escape(kind)}" data-from="{escape(src)}" data-to="{escape(dst)}" '
        f'data-key="{escape(_line_key(src, dst))}"/>'
        for src, dst, kind in sorted(links, key=lambda ln: (ln[1], ln[0]))
    )
    parts.append("</svg></div>")
    return "\n".join(parts)


#: T7: the selector's geometry — a leaf column, a row per depth, a node's radius, the margins.
SEL_COL = 26
SEL_ROW = 30
SEL_R = 8
SEL_MARGIN = 14


def _tidy(
    children: Mapping[str, Sequence[str]], top: str
) -> tuple[dict[str, tuple[float, float]], float, float]:
    """A typical tree: leaves evenly spaced along the bottom in depth-first order, every parent
    centred over its children, one row per depth. Returns each node's centre and the size."""
    at: dict[str, tuple[float, float]] = {}
    slot = [0]

    def place(key: str, depth: int) -> float:
        kids = children.get(key, ())
        x: float
        if not kids:
            x = SEL_MARGIN + slot[0] * SEL_COL
            slot[0] += 1
        else:
            xs = [place(k, depth + 1) for k in kids]
            x = (xs[0] + xs[-1]) / 2
        at[key] = (x, SEL_MARGIN + depth * SEL_ROW)
        return x

    place(top, 0)
    width = SEL_MARGIN * 2 + max(slot[0] - 1, 0) * SEL_COL
    height = SEL_MARGIN * 2 + max(y for _x, y in at.values()) - SEL_MARGIN
    return at, width, height


def _selector_svg(  # noqa: PLR0913, PLR0912, PLR0915 — the selector, nodes and edges
    vs: Mapping[str, View],
    result: routes.Routes,
    rows: Mapping[str, Mapping[str, Any]],
    *,
    names: dag.Prefix,
    labels: dag.Labels,
    proof_labels: Sequence[str],
) -> str:
    """R5, restated by T7 (the owner, 2026-10-18): the selector tree as a small, typical tree
    diagram — a dot per node, straight lines, leaves numbered, the root statement above the top
    split when they differ, one leaf per proof — with every node's words (what it is, the route
    its edge chose) in ``data-words`` and its ``<title>`` for the hover, none drawn."""
    sel = {k: v for k, v in vs.items() if k == SEL_PREFIX or k.startswith(SEL_PREFIX + "/")}
    proofs = [k for k in vs if k.startswith(PROOF)]
    if not sel and not proofs:
        return ""
    children: dict[str, list[str]] = {}
    for key, v in sel.items():
        if v.parent is not None:
            children.setdefault(v.parent, []).append(key)
    top = SEL_PREFIX if SEL_PREFIX in sel else None
    root = result.root
    has_root = (EDGE + SEL_PREFIX) in vs or (top is None and proofs)
    hang = "root" if has_root else top
    if has_root and top is not None:
        children.setdefault("root", []).append(top)
    for k in proofs:
        if hang is not None:
            children.setdefault(hang, []).append(k)
    assert hang is not None
    kinds: dict[str, str] = {}
    words: dict[str, str] = {}
    glyph: dict[str, str] = {}
    forked = {
        v.parent
        for v in sel.values()
        if v.side is not None and v.parent in sel and sel[v.parent].side is None
    }
    for key, v in sel.items():
        n = len(v.sets)
        # F04-T55 (D-25 v3.46): a set says which way it settles the problem; the top fork,
        # when it is by side, says so; a side's own node says its side.
        if v.kind == "leaf":
            kinds[key] = "kind-leaf"
            s = result.sets[v.index - 1]
            noun = "statement" if s.remaining == 1 else "statements"
            way = routes_view.settles(s)
            words[key] = f"Set {v.index} ({way}): {s.remaining} open {noun} of {s.total}"
            glyph[key] = str(v.index)
        else:
            split = v.split or root
            label = dag.label_of(split, names, labels)
            kinds[key] = "kind-node"
            if key in forked:
                words[key] = (
                    f"{label}: {n} set{'' if n == 1 else 's'} settle it, proving or refuting"
                )
            else:
                words[key] = f"{label}: {n} set{'' if n == 1 else 's'} choose a route here"
        own_side = v.side if v.parent in forked else None
        if own_side is not None:
            side_words = routes_view.SIDE_WORDS.get(own_side, own_side)
            words[key] = (
                f"{words[key]} — {side_words}"
                if v.kind == "leaf"
                else f"{side_words}: {n} set{'' if n == 1 else 's'} choose a route at "
                f"{dag.label_of(v.split or root, names, labels)}"
            )
        if v.parent is not None and v.split is not None:
            at_label = dag.label_of(v.split, names, labels)
            how = (
                routes_view.approach_of(v.route, rows, at_label)
                if v.route is not None
                else f"{at_label}: taken directly"
            )
            words[key] += f" — via {how}"
    if has_root:
        kinds["root"] = "kind-root"
        words["root"] = f"{dag.label_of(root, names, labels)}: the problem's own statement"
    for k, label in zip(proofs, proof_labels, strict=False):
        kinds[k] = "kind-proof"
        words[k] = label
        glyph[k] = "P"
    pos, width, height = _tidy(children, hang)
    parts = [
        f'<svg class="selector" viewBox="0 0 {width:g} {height:g}" width="{width:g}" '
        f'height="{height:g}" role="img" aria-label="sufficient sets">'
    ]
    for parent, kids in children.items():
        for child in kids:
            (x0, y0), (x1, y1) = pos[parent], pos[child]
            view_key = EDGE + child
            ev = vs.get(view_key)
            attrs = ""
            inner = ""
            if ev is not None:
                attrs = (
                    f' data-view="{escape(view_key)}" data-sets="{escape(" ".join(ev.sets))}" '
                    'role="button" tabindex="0" aria-pressed="false"'
                )
                inner = f"<title>{escape(words[child])}</title>"
            # F04-T55: the edge into a node under a side wears the side, like the node.
            cv = vs.get(child)
            side_cls = f" side-{escape(cv.side)}" if cv is not None and cv.side else ""
            parts.append(
                f'<path class="sel-edge{side_cls}" data-from="{escape(parent)}" '
                f'data-to="{escape(child)}"{attrs} d="M{x0:g} {y0:g}L{x1:g} {y1:g}">{inner}</path>'
            )
    for key, (x, y) in pos.items():
        nv = vs.get(key)
        own = ""
        side_cls = ""
        if nv is not None:
            own = (
                f' data-view="{escape(key)}" data-sets="{escape(" ".join(nv.sets))}" '
                'role="button" tabindex="0" aria-pressed="false"'
            )
            side_cls = f" side-{escape(nv.side)}" if nv.side else ""
        # T10 (the owner): a set is a numbered circle; a fork is a small square and the root a
        # dashed one, so no mark here is the circle the drawing uses for a statement.
        if key in glyph:
            mark = f'<circle class="dot" r="{SEL_R}"/><text y="3.5">{escape(glyph[key])}</text>'
        elif kinds[key] == "kind-root":
            mark = '<rect class="dot" x="-7" y="-7" width="14" height="14" rx="3"/>'
        else:
            mark = '<rect class="dot" x="-5" y="-5" width="10" height="10" rx="1.5"/>'
        parts.append(
            f'<a href="#"><g class="sel-node {kinds[key]}{side_cls}"{own} data-key="{escape(key)}" '
            f'data-words="{escape(words[key])}" '
            f'transform="translate({x:g},{y:g})"><title>{escape(words[key])}</title> '
            f"{mark}</g></a>"
        )
    parts.append("</svg>")
    return "\n".join(parts)


#: F27-R13: the toggle's words. Ticked (the default) the sets stop at a proved statement; unticked
#: each proved statement shows what its proof rests on.
FOLLOW_LABEL = "Stop at proved statements"
FOLLOW_TITLE = (
    "Ticked: a proved statement ends a set. Unticked: beneath each proved statement, what its "
    "proof rests on, as the gate measured it; the sets and their open statements are the same."
)


def _follow_toggle() -> str:
    return (
        f'<label class="sel-follow" title="{escape(FOLLOW_TITLE)}" hidden>'
        '<input type="checkbox" class="follow-proved" checked> '
        f"{escape(FOLLOW_LABEL)}</label>"
    )


def _toggle(hidden: int, shelved: int = 0) -> str:
    """The view-toggle's words: how many statements ``all`` adds to ``routes``, and (F31-T10)
    how many of those are shelved rather than on no route."""
    if not hidden:
        return ""
    noun = "statement" if hidden == 1 else "statements"
    if not shelved:
        detail, why = "", " on no route"
    elif shelved == hidden:
        detail = why = f" ({shelved} shelved)"
    else:
        detail = why = f" ({hidden - shelved} on no route, {shelved} shelved)"
    return (
        f'<button type="button" class="chip view-toggle" data-view="{ALL}" aria-pressed="false" '
        f'data-shown-label="Hide the {hidden} {noun}{why}" hidden>'
        f"Show {hidden} more {noun}{detail}</button>"
    )


def _shelved_titles(
    rows: Mapping[str, Mapping[str, Any]], titles: dict[str, str]
) -> dict[str, Mapping[str, Any]]:
    """F31-T10 (R7): the cause on hover, in the signer's words (escaped by the markup), added
    to each drawn shelved statement's title; returns those statements' ``shelved`` facts."""
    found = {nid: rows[nid]["shelved"] for nid in titles if rows.get(nid, {}).get("shelved")}
    for nid, fact in found.items():
        titles[nid] += f"; shelved by {fact.get('by')} on {fact.get('date')}: {fact.get('cause')}"
    return found


def _hidden_counts(
    vs: Mapping[str, View], d: routes_view.Drawn, shelved_rows: Mapping[str, Any]
) -> tuple[int, int]:
    """R4, F31-T10: what the toggle counts — statements ``all`` adds to ``routes``, never
    junctions (a cut route's junction is off ``routes`` too), and how many are shelved."""
    off_route = [n for n in vs[ALL].nodes if n not in d.junctions and n not in vs[ROUTES].nodes]
    return len(off_route), sum(1 for n in off_route if n in shelved_rows)


def drawing(  # noqa: PLR0913 — the page's inputs
    graph: Mapping[str, Any],
    frontier_entries: Iterable[Mapping[str, Any]],
    *,
    href: Mapping[str, str],
    prefix: str | None = None,
    nodes: Sequence[Mapping[str, Any]] | None = None,
    proofs: Sequence[dag.ProofMarks] = (),
    proof_labels: Sequence[str] = (),
    outlines: Mapping[str, int] | None = None,
    titles: Mapping[str, str] | None = None,
    literature: dag.Literature = None,
) -> Drawing:
    """The page's drawing. ``nodes`` (the page's view of the rows, a status renamed for the
    key) stands in for ``graph["nodes"]`` in the drawing and the layouts; the routes and sets
    are read from ``graph`` as the MCP tool reads them (F27-Q1). ``literature`` (F04-T54) marks
    the named pills with their literature status and feeds nothing else: the views, layouts,
    selector and table are the same with or without it."""
    entries = list(frontier_entries)
    result = routes.read(graph, entries)
    # F27-R13: the same sets read past their proved statements, for the page's toggle
    follow = routes.read(graph, entries, at_proved="follow")
    drawn_graph: dict[str, Any] = dict(graph)
    if nodes is not None:
        drawn_graph["nodes"] = list(nodes)
    rows = {str(n["node_id"]): n for n in drawn_graph["nodes"] if isinstance(n, Mapping)}
    d = routes_view.drawn(drawn_graph, result)
    vs = views(drawn_graph, result, proofs=proofs, follow=follow)
    labels = dag.labels_of(rows.values())
    root = str(graph.get("root"))
    names: dag.Prefix = (prefix, root) if prefix else None
    lays = layouts(rows.values(), vs, root=root, prefix=prefix, labels=labels)
    ready = {c.node: c for c in closing.closable(graph)}
    band = vs[BAND].nodes if BAND in vs else ()
    full_titles = {
        nid: f"{nid}{' (' + labels[nid] + ')' if nid in labels else ''}: {_status_of(rows, nid)}"
        + (f"; {routes_view.closable_words(ready[nid], ready)}" if nid in ready else "")
        for nid in (*vs[ALL].nodes, *band)
        if nid not in d.junctions
    }
    full_titles.update(titles or {})
    # F30-T11: a stated pointer is words on the pill, never a line.
    for nid in band:
        target = rows.get(nid, {}).get("proposed_for")
        if target and nid in full_titles:
            full_titles[nid] += f"; proposed for: {dag.label_of(str(target), names, labels)}"
    shelved_rows = _shelved_titles(rows, full_titles)  # F31-T10 (R7)
    svg = _dag_svg(
        vs,
        lays,
        d,
        rows,
        href=href,
        names=names,
        labels=labels,
        titles=full_titles,
        outlines=outlines or {},
        closable=ready,
        literature=literature,
    )
    # A target with no route has no sets worth choosing (its one "set" is the root taken
    # directly): no selector and no table, unless it has proofs to list.
    if not d.junctions:
        vs = {
            k: v for k, v in vs.items() if not (k == TOP or k.startswith((TOP + "/", EDGE, FOLLOW)))
        }
        result = replace(result, sets=())
        follow = replace(follow, sets=())
    leaf_of = {v.sets[0]: k for k, v in vs.items() if v.kind == "leaf" and not k.startswith(FOLLOW)}
    marks: set[str] = set()
    if any(r.live for r in d.junctions.values()):
        marks.add("route-and")
    if any(not r.live for r in d.junctions.values()):
        marks.add("route-dead")
    if any(n >= 2 for n in d.alternatives.values()):
        marks.add("route-or")
    if ready:
        marks.add("closable")
    # F04-T55 (D-30 v3.46): the relation trunks the drawing has, each keyed.
    for label in (rows[v].get("relation") for v in d.below.get(root, []) if v in rows):
        if label in routes_view.TRUNK_LABELS:
            marks.add(f"relation-{label}")
    if any(n in shelved_rows for n in vs[ALL].nodes):
        marks.add("shelved")  # F31-T10
    hidden, shelved_hidden = _hidden_counts(vs, d, shelved_rows)
    doc = json.dumps(layouts_document(lays), separators=(",", ":")).replace("</", "<\\/")
    merged_rows = list(merged_nodes(rows.values(), d, root).values())
    crossing = [ln for ln in dag.lines(merged_rows) if (ln[0] in set(band)) != (ln[1] in set(band))]
    # F30-T13: the band's own lines are links too, drawn only while lit (a crux to its holes
    # directly: the column draws no junction).
    column = {b for b in band if b not in d.junctions}
    crossing += [
        ln
        for ln in dag.lines([dict(rows[i]) for i in sorted(column)])
        if ln[0] in column and ln[1] in column
    ]
    crossing = [ln for ln in crossing if ln[0] in column or ln[1] in column]
    band_svg = _band_svg(
        vs,
        lays,
        d,
        rows,
        href=href,
        names=names,
        labels=labels,
        titles=full_titles,
        outlines=outlines or {},
        closable=ready,
        literature=literature,
        links=crossing,
    )
    return Drawing(
        svg=svg,
        selector=_selector_svg(
            vs, result, rows, names=names, labels=labels, proof_labels=proof_labels
        ),
        table=routes_view.table(result, prefix, views=leaf_of, follow=follow)
        if result.sets
        else "",
        layouts_json=f'<script type="application/json" id="graph-layouts">{doc}</script>',
        toggle=_toggle(hidden, shelved_hidden),
        marks=frozenset(marks),
        sets=len(result.sets),
        hidden=hidden,
        follow_toggle=_follow_toggle() if result.sets else "",
        band=band_svg,
        shelved=shelved_hidden,
        routes=tuple(
            RouteRow(
                r.id,
                r.node,
                r.partial,
                r.approach,
                shelving_words(r, rows, d.below.get(rid, [])),
                cut=bool(d.below.get(rid))
                and all(rows.get(h, {}).get("shelved") for h in d.below.get(rid, [])),
            )
            for rid, r in d.junctions.items()
            if r.node not in set(band)
        ),
    )
