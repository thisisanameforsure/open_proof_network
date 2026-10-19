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
    merged = merged_nodes(rows, d)
    root = result.root
    out: dict[str, View] = {}
    out[ALL] = _view(ALL, ALL, merged, merged)
    out[ROUTES] = _view(ROUTES, ROUTES, merged, [*d.statements, *d.junctions] or [root])
    out.update(_set_views(graph, result, d, merged, prefix=""))
    if follow is not None:
        out.update(_set_views(graph, follow, d, merged, prefix=FOLLOW))
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

    def visit(sel: routes.Selector, key: str, parent: str | None, split_on: str | None) -> None:
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


# -- the markup (T2) ----------------------------------------------------------------------------

#: The selector's edge labels are cut here; the full approach is in the edge's ``<title>``.
APPROACH_MAX = 40
SEL_PREFIX = "sel"


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


def _line_key(src: str, dst: str) -> str:
    return f"{src}>{dst}"


def _status_of(rows: Mapping[str, Mapping[str, Any]], nid: str) -> str:
    return str(rows[nid].get("status")) if nid in rows else "route"


def _junction_markup(r: routes.Route, x: int, y: int, hidden: bool) -> str:
    holes = r.summary.holes
    words = (
        f"route {r.id}: {holes} hole{'' if holes == 1 else 's'}, all needed"
        if r.live
        else f"route {r.id}: closes nothing (a hole is refuted, defective, abandoned, "
        "superseded or not traced)"
    )
    cx, cy = JUNCTION_W // 2, dag.NODE_H // 2
    mark = (
        f'<circle class="and-mark" cx="{cx}" cy="{cy}" r="5"/>'
        if r.live
        else f'<circle class="dead-mark" cx="{cx}" cy="{cy}" r="5"/>'
        f'<path class="dead-cross" d="M{cx - 3} {cy - 3}l6 6m0 -6l-6 6"/>'
    )
    off = " off-view" if hidden else ""
    return (
        f'<g class="junction {"live" if r.live else "dead"}{off}" data-route="{escape(r.id)}" '
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
) -> str:
    cls = f"node status-{escape(status)}"
    if proved:
        cls += " proved"
    if closable:
        cls += " closable"
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
        f'<rect class="pill" width="{p.w}" height="{dag.NODE_H}" rx="8"/>'
        f'<circle cx="16" cy="{dag.NODE_H // 2}" r="4"/>{asm}'
        f'<text x="28" y="{dag.NODE_H // 2 + 5}">{escape(label)}</text> '
        f'<circle class="halo" cx="{p.w - 14}" cy="{dag.NODE_H // 2}" r="3"/>'
        + dag.outline_mark(outline, p.w)
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
) -> str:
    opening = lays[ROUTES]
    shown_nodes = set(vs[ROUTES].nodes)
    shown_lines = {(s, t) for s, t, _k in vs[ROUTES].lines}
    # Every node's place: the opening layout's, else the first layout that has it.
    at: dict[str, dag.Placed] = {p.node_id: p for p in opening.placed}
    edge_at: dict[tuple[str, str], dag.Edge] = {(e.src, e.dst): e for e in opening.edges}
    for key, lay in lays.items():
        if key == ROUTES:
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
    for nid in vs[ALL].nodes:
        p = at[nid]
        hidden = nid not in shown_nodes
        if nid in d.junctions:
            parts.append(_junction_markup(d.junctions[nid], p.x, p.y, hidden))
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
            )
        )
    parts.append("</svg>")
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
    for key, v in sel.items():
        if v.kind == "leaf":
            kinds[key] = "kind-leaf"
            s = result.sets[v.index - 1]
            noun = "statement" if s.remaining == 1 else "statements"
            words[key] = f"Set {v.index}: {s.remaining} open {noun} of {s.total}"
            glyph[key] = str(v.index)
        else:
            split = v.split or root
            label = dag.label_of(split, names, labels)
            kinds[key] = "kind-node"
            n = len(v.sets)
            words[key] = f"{label}: {n} set{'' if n == 1 else 's'} choose a route here"
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
            parts.append(
                f'<path class="sel-edge" data-from="{escape(parent)}" data-to="{escape(child)}"'
                f'{attrs} d="M{x0:g} {y0:g}L{x1:g} {y1:g}">{inner}</path>'
            )
    for key, (x, y) in pos.items():
        nv = vs.get(key)
        own = ""
        if nv is not None:
            own = (
                f' data-view="{escape(key)}" data-sets="{escape(" ".join(nv.sets))}" '
                'role="button" tabindex="0" aria-pressed="false"'
            )
        # T10 (the owner): a set is a numbered circle; a fork is a small square and the root a
        # dashed one, so no mark here is the circle the drawing uses for a statement.
        if key in glyph:
            mark = f'<circle class="dot" r="{SEL_R}"/><text y="3.5">{escape(glyph[key])}</text>'
        elif kinds[key] == "kind-root":
            mark = '<rect class="dot" x="-7" y="-7" width="14" height="14" rx="3"/>'
        else:
            mark = '<rect class="dot" x="-5" y="-5" width="10" height="10" rx="1.5"/>'
        parts.append(
            f'<a href="#"><g class="sel-node {kinds[key]}"{own} data-key="{escape(key)}" '
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


def _toggle(hidden: int) -> str:
    if not hidden:
        return ""
    noun = "statement" if hidden == 1 else "statements"
    return (
        f'<button type="button" class="chip view-toggle" data-view="{ALL}" aria-pressed="false" '
        f'data-shown-label="Hide the {hidden} {noun} on no route" hidden>'
        f"Show {hidden} more {noun}</button>"
    )


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
) -> Drawing:
    """The page's drawing. ``nodes`` (the page's view of the rows, a status renamed for the
    key) stands in for ``graph["nodes"]`` in the drawing and the layouts; the routes and sets
    are read from ``graph`` as the MCP tool reads them (F27-Q1)."""
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
    full_titles = {
        nid: f"{nid}{' (' + labels[nid] + ')' if nid in labels else ''}: {_status_of(rows, nid)}"
        + (f"; {routes_view.closable_words(ready[nid], ready)}" if nid in ready else "")
        for nid in vs[ALL].nodes
        if nid not in d.junctions
    }
    full_titles.update(titles or {})
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
    hidden = len(vs[ALL].nodes) - len(vs[ROUTES].nodes)
    doc = json.dumps(layouts_document(lays), separators=(",", ":")).replace("</", "<\\/")
    return Drawing(
        svg=svg,
        selector=_selector_svg(
            vs, result, rows, names=names, labels=labels, proof_labels=proof_labels
        ),
        table=routes_view.table(result, prefix, views=leaf_of, follow=follow)
        if result.sets
        else "",
        layouts_json=f'<script type="application/json" id="graph-layouts">{doc}</script>',
        toggle=_toggle(hidden),
        marks=frozenset(marks),
        sets=len(result.sets),
        hidden=hidden,
        follow_toggle=_follow_toggle() if result.sets else "",
    )
