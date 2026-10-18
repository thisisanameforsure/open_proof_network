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
without a choice), ``edge/<child key>``, ``proof/<k>``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from opn_gate import routes
from opn_site import dag, routes_view

#: A junction is a dot in a box this wide (as the routes drawing drew it, F27-T3).
JUNCTION_W = routes_view.JUNCTION_W
ALL = "all"
ROUTES = "routes"
TOP = "sel"
EDGE = "edge/"
PROOF = "proof/"
DIRECT = "direct"


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


def merged_nodes(
    graph_nodes: Iterable[Mapping[str, Any]], d: routes_view.Drawn
) -> dict[str, dict[str, Any]]:
    """The layout's node dicts keyed by id: each statement with the hole dependencies of its
    drawn routes rerouted through those routes' junctions (its ``deps`` and ``uses`` lose the
    holes and its ``deps`` gain the junction ids), and one dict per junction whose ``deps`` are
    its holes. Everything else a row carries (``lemmas``, ``proposed_for``, the status) stays."""
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
    return out


def _subset(merged: Mapping[str, Mapping[str, Any]], ids: Iterable[str]) -> list[dict[str, Any]]:
    keep = [i for i in dict.fromkeys(ids) if i in merged]
    return [dict(merged[i]) for i in keep]


def _view(
    key: str,
    kind: str,
    merged: Mapping[str, Mapping[str, Any]],
    ids: Iterable[str],
    **facts: Any,
) -> View:
    rows = _subset(merged, ids)
    return View(key, kind, tuple(r["node_id"] for r in rows), tuple(dag.lines(rows)), **facts)


def _on(s: routes.SufficientSet, root: str, d: routes_view.Drawn) -> set[str]:
    """What a set lights (F27's ``lit_sets``): the root, its statements, assemblies, variant,
    and the junctions of the routes it uses."""
    on = {root, *s.statements, *s.assemblies}
    if s.variant:
        on.add(s.variant)
    on.update(rid for rid in s.routes if rid in d.junctions)
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
) -> dict[str, View]:
    """Every view of a target, keyed (see the module), the selector's in depth-first order."""
    d = routes_view.drawn(graph, result)
    rows = [n for n in graph.get("nodes") or [] if isinstance(n, Mapping)]
    merged = merged_nodes(rows, d)
    root = result.root
    out: dict[str, View] = {}
    out[ALL] = _view(ALL, ALL, merged, merged)
    out[ROUTES] = _view(ROUTES, ROUTES, merged, [*d.statements, *d.junctions] or [root])
    index = {s.id: k for k, s in enumerate(result.sets, start=1)}
    on = {s.id: _on(s, root, d) for s in result.sets}

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

    def visit(sel: routes.Selector, key: str, parent: str | None, split_on: str | None) -> None:
        beneath = _leaves(sel)
        if sel.set is not None:
            out[key] = _view(
                key,
                "leaf",
                merged,
                sorted(on[sel.set]),
                sets=beneath,
                route=sel.route,
                split=split_on,
                index=index[sel.set],
                parent=parent,
            )
        else:
            out[key] = _view(
                key,
                "node",
                merged,
                sorted(family(sel)),
                sets=beneath,
                route=sel.route,
                split=sel.node,
                parent=parent,
            )
        if split_on is not None:
            # The edge into this node: from the statement its parent split on, through the
            # route it chose (or that statement alone when taken directly), over what every
            # set beneath shares, down to and including this node's own split (Q3).
            seg = _segment(split_on, sel.route, sel.node, common(sel), d)
            out[EDGE + key] = View(
                EDGE + key,
                "edge",
                tuple(seg),
                tuple(dag.lines(_subset(merged, seg))),
                sets=beneath,
                route=sel.route,
                split=split_on,
                parent=key,
            )
        for c in sel.children:
            if c.route is not None:
                part = c.route
            elif c.set is not None and sel.node is None:
                part = f"set:{c.set}"
            else:
                part = DIRECT
            visit(c, f"{key}/{part}", key, sel.node)

    tree = routes.selector_tree(result)
    if tree.sets:
        visit(tree, TOP, None, None)
        if tree.node is not None and tree.node != root:
            # The trunk: root down to the first split, common to every set.
            shared = common(tree)
            first = next((rid for rid in d.below.get(root, []) if rid in shared), None)
            seg = _segment(root, first, tree.node, shared, d)
            out[EDGE + TOP] = View(
                EDGE + TOP,
                "edge",
                tuple(seg),
                tuple(dag.lines(_subset(merged, seg))),
                sets=_leaves(tree),
                split=root,
                parent=TOP,
            )
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
        elif kind == "edge proposed":
            rows[src]["proposed_for"] = dst
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
) -> dag.Layout:
    return dag.layout(
        _rows_for(view, status),
        root=root if root in view.nodes else None,
        prefix=prefix,
        widths=widths,
        labels=labels,
        order=order,
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
    centre of each node in ``all`` (Q2). A junction (an id no row has) is a dot-wide box."""
    status = statuses(graph_nodes)
    widths = junction_widths(vs[ALL], status)
    out: dict[str, dag.Layout] = {}
    seed: dict[str, float] | None = None
    for key, v in vs.items():
        lay = layout_view(
            v, status, root=root, prefix=prefix, widths=widths, labels=labels, order=seed
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
    each line's bend points; ids and numbers only."""
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
    }
