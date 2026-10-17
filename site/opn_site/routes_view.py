"""The problem page's Routes section (F27-T3; R10, R11; D-25 v3.40, D-36).

A target read as an AND-OR graph, drawn from ``opn_gate.routes`` over the same two products the
MCP tool reads (``graph.json`` and the target's ``frontier.json`` entries), so the page and the
tool cannot disagree (F27-Q1).

The drawing reuses the statement graph's layout (``dag.layout``) over a graph of its own: each
statement on a way to close the root, and each route (a merged decomposition) as a small junction
box between its node and its holes. A route's junction is a filled dot (AND: every hole is
needed); a statement that two or more routes, or at the root a ``resolves`` variant, could close
carries a hollow diamond on its lower edge (OR: any one). Each statement is a pie with one wedge
per sufficient set holding it, coloured by set; proved statements are drawn solid, open ones pale
with a dashed ring. The layout depends on the graph alone: what a reader selects only changes
classes, never a coordinate (R10).

Every node is a ``<g>`` with ``data-node`` (a junction's with ``data-route``), every line a
``<path>`` with ``data-from`` and ``data-to``, every wedge carries ``data-set``, and every node
and line lists in ``data-sets`` the sets it belongs to, so ``routes.js`` lights a set without
knowing the graph, and the tests can read the structure. Without the script the drawing and the
table are complete.

F29-T6 (R10; D-25 v3.44): the selector tree (``routes.selector_tree``, built from the sets) is
boxed as "Sufficient sets" down the drawing's left edge, where F27-T7's set labels stood: one row
per node of the tree in depth-first order, indented by depth, a branch naming the statement its
route is a route of and the route's approach, a leaf one set with its swatch. Every row carries
in ``data-sets`` the sets beneath it, so the script lights a branch as it lights a set.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace
from html import escape
from typing import Any

from opn_gate import closing, routes
from opn_gate.graph import HOLE_ORIGINS, HOLE_SEPARATOR
from opn_site import dag

#: The hues a set may wear (F27 §6): more than this are drawn grey and the section says so.
HUES = 8
#: A junction is a dot in a box this wide (``dag.layout``'s ``widths``).
JUNCTION_W = 16
#: A statement is a pie and its label; the pie's centre and radius in the box.
PIE_X = 18
PIE_R = 10
#: The ring (solid when proved, dashed when open) sits just outside the pie, so a dashed ring
#: never cuts into a set's colour.
RING_R = 13
#: An open statement's pie is hollow to this radius.
CORE_R = 4
LABEL_X = 36
#: Room for the label after its text (the box is ``LABEL_X`` + the text + this).
LABEL_END = 12
DIAMOND = 6
#: F27-T7: the column down the drawing's left edge that holds the selector (F29-T6, where one
#: label per set stood); the statements and lines are drawn to its right, so no row covers one.
#: This is its least width; the box grows to its longest row (``selector_width``).
LABEL_COLUMN = 96
SET_LABEL_W = 80
SET_LABEL_H = 28
SET_LABEL_GAP = 8
#: F29-T6: the selector's rows — indented this much per depth, the words in the sans face at
#: about this width a character, cut at this many characters (the whole text stays in the
#: row's ``<title>``), under a heading this tall, inside a box with this much padding.
SEL_INDENT = 14
SEL_CHAR_W = 6.6
SEL_TEXT_MAX = 40
SEL_HEAD_H = 26
SEL_PAD = 8

DEAD = routes.DEAD_STATUSES

INTRO = (
    "A route is a merged decomposition of a statement: a partial proof whose holes are all "
    "needed. A statement with several routes can be closed by any one of them, or proved "
    "directly. A sufficient set is a set of statements whose proofs would close the problem's "
    "own statement, with the assemblies on the way still to submit: the closing proofs of the "
    "decomposed statements the set's routes pass through. The sets are listed in the record's "
    "order and nothing is ranked. Each open statement in a set could also be proved directly, "
    "which drops what is beneath it; those coarser sets are not listed here "
    "(<code>list_sufficient_sets</code> returns them with <code>cut: any</code>)."
)


@dataclass
class Drawn:
    """The graph the drawing lays out: statements and junctions, each with what it is drawn
    above, and per element the sets it belongs to."""

    rows: dict[str, Mapping[str, Any]]
    statements: list[str] = field(default_factory=list)
    junctions: dict[str, routes.Route] = field(default_factory=dict)
    below: dict[str, list[str]] = field(default_factory=dict)
    alternatives: dict[str, int] = field(default_factory=dict)


def _hole_dep(node_id: str, dep: str, rows: Mapping[str, Mapping[str, Any]]) -> bool:
    row = rows.get(dep)
    return (
        row is not None
        and dep.startswith(node_id + HOLE_SEPARATOR)
        and str(row.get("origin")) in HOLE_ORIGINS
    )


def plain_deps(node_id: str, rows: Mapping[str, Mapping[str, Any]], held: set[str]) -> list[str]:
    """A statement's declared dependencies that are not its holes: what a direct proof of it
    needs (D-12 v3.19: a decomposition never blocks its node)."""
    out = []
    for raw in rows[node_id].get("deps") or []:
        dep = str(raw)
        if dep in rows and dep not in held and not _hole_dep(node_id, dep, rows):
            out.append(dep)
    return out


def drawn(graph: Mapping[str, Any], result: routes.Routes) -> Drawn:
    """Every statement on a way to close the root: through routes' holes (live or dead, so a
    dead route is seen), through declared non-hole dependencies, and at the root through each
    ``resolves`` variant. A line that would return to a statement on its own path is not drawn
    (the enumeration drops such a route too, F27-R5)."""
    rows = {str(n["node_id"]): n for n in graph.get("nodes") or [] if isinstance(n, Mapping)}
    out = Drawn(rows)
    if result.root not in rows:
        return out
    by_node: dict[str, list[routes.Route]] = {}
    for r in result.routes:
        by_node.setdefault(r.node, []).append(r)
    variants = [
        k for k, row in rows.items() if k != result.root and row.get("relation") == routes.RESOLVES
    ]
    seen: set[str] = set()

    def visit(node_id: str, path: tuple[str, ...]) -> None:
        if node_id in seen:
            return
        seen.add(node_id)
        out.statements.append(node_id)
        here = (*path, node_id)
        mine = by_node.get(node_id, [])
        held = {str(h.node) for r in mine for h in r.holes if h.node}
        below: list[str] = []
        for r in mine:
            if not any(h.node in rows for h in r.holes):
                continue  # an unresolved route draws nothing (F27-R2)
            out.junctions[r.id] = r
            below.append(r.id)
            out.below[r.id] = []
            for h in r.holes:
                if h.node in rows and h.node not in here:
                    out.below[r.id].append(str(h.node))
                    visit(str(h.node), here)
        for dep in plain_deps(node_id, rows, held):
            if dep not in here:
                below.append(dep)
                visit(dep, here)
        alts = len([j for j in below if j in out.junctions])
        if node_id == result.root:
            for v in variants:
                if v not in here:
                    below.append(v)
                    alts += 1
                    visit(v, here)
        out.below[node_id] = below
        out.alternatives[node_id] = alts

    visit(result.root, ())
    return out


def lit_sets(
    d: Drawn, result: routes.Routes
) -> tuple[dict[str, list[str]], dict[tuple[str, str], list[str]]]:
    """Per element (a statement or a junction) and per line ``(lower, upper)``, the ids of the
    sets it belongs to: the root, the set's statements, its assemblies and its variant; the
    junctions of its routes, their lines to their node and to their holes; a statement's line
    to a declared dependency when both are in the set; and the root's line to the variant."""
    nodes: dict[str, list[str]] = {}
    lines: dict[tuple[str, str], list[str]] = {}

    def add(key: str, sid: str) -> None:
        nodes.setdefault(key, []).append(sid)

    def line(lower: str, upper: str, sid: str) -> None:
        if lower in d.below.get(upper, []):
            lines.setdefault((lower, upper), []).append(sid)

    for s in result.sets:
        members = set(s.statements)
        on = {result.root, *members, *s.assemblies, *([s.variant] if s.variant else [])}
        for v in on:
            add(v, s.id)
        for rid in s.routes:
            r = d.junctions.get(rid)
            if r is None:
                continue
            add(rid, s.id)
            line(rid, r.node, s.id)
            for h in d.below.get(rid, []):
                line(h, rid, s.id)
        for m in members:
            for dep in d.below.get(m, []):
                if dep in members:
                    line(dep, m, s.id)
        if s.variant:
            line(s.variant, result.root, s.id)
    return nodes, lines


def hue(k: int) -> str:
    """The class of the ``k``-th set (from 1): its own hue up to ``HUES``, grey beyond."""
    return f"set-{k}" if k <= HUES else "set-more"


def _num(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def pie(set_ids: list[str], index: Mapping[str, int]) -> str:
    """One wedge per set, clockwise from the top, each carrying ``data-set``."""
    if not set_ids:
        return ""
    if len(set_ids) == 1:
        sid = set_ids[0]
        return (
            f'<circle class="wedge {hue(index[sid])}" data-set="{escape(sid)}" '
            f'cx="{PIE_X}" cy="{dag.NODE_H // 2}" r="{PIE_R}"/>'
        )
    cy = dag.NODE_H / 2
    step = 2 * math.pi / len(set_ids)
    out = []
    for k, sid in enumerate(set_ids):
        a0, a1 = -math.pi / 2 + k * step, -math.pi / 2 + (k + 1) * step
        x0, y0 = PIE_X + PIE_R * math.cos(a0), cy + PIE_R * math.sin(a0)
        x1, y1 = PIE_X + PIE_R * math.cos(a1), cy + PIE_R * math.sin(a1)
        large = 1 if step > math.pi else 0
        out.append(
            f'<path class="wedge {hue(index[sid])}" data-set="{escape(sid)}" '
            f'd="M{PIE_X} {_num(cy)}L{_num(x0)} {_num(y0)}'
            f'A{PIE_R} {PIE_R} 0 {large} 1 {_num(x1)} {_num(y1)}Z"/>'
        )
    return "".join(out)


def state_of(status: str) -> str:
    if status == routes.PROVED:
        return "proved"
    if status in DEAD:
        return "dead"
    return "open"


@dataclass(frozen=True)
class Section:
    """What the page needs: the markup, and whether there is any."""

    html: str
    sets: int


def section(
    graph: Mapping[str, Any],
    frontier_entries: Iterable[Mapping[str, Any]],
    *,
    href: Mapping[str, str],
    prefix: str | None = None,
) -> Section:
    """The Routes section, or ``Section("", 0)`` when nothing is drawn: a target whose graph has
    no route reachable from its root."""
    result = routes.read(graph, list(frontier_entries))
    d = drawn(graph, result)
    if not d.junctions:
        return Section("", 0)
    ready = {c.node: c for c in closing.closable(graph)}
    return Section(
        '<section class="routes-section" id="routes">'
        '<div class="section-head"><div><h2>Routes</h2>'
        f'<p class="cue">{INTRO}</p></div></div>'
        '<div class="routes-grid">'
        f'<div class="routes-wrap card">{legend(result)}'
        '<div class="routes-scroll">'
        f"{svg(d, result, href=href, prefix=prefix, closable=ready)}</div>"
        f"{closable_line(ready, href, prefix, result.root)}</div>"
        f"{table(result, prefix)}"
        "</div></section>",
        len(result.sets),
    )


def svg(
    d: Drawn,
    result: routes.Routes,
    *,
    href: Mapping[str, str],
    prefix: str | None = None,
    closable: Mapping[str, closing.Closable] | None = None,
) -> str:
    """The drawing: statements as pies, routes as junctions, laid out by ``dag.layout``. A
    closable statement (F28, v3.41) keeps its open look and gains the filled assembly mark."""
    closable = closable or {}
    names: dag.Prefix = (prefix, result.root) if prefix else None
    labels = dag.labels_of(d.rows.values())  # F29-T5 (R9): pills by label, ids in titles
    widths: dict[str, int] = {j: JUNCTION_W for j in d.junctions}
    for v in d.statements:
        widths[v] = LABEL_X + round(dag.CHAR_W * len(dag.label_of(v, names, labels))) + LABEL_END
    nodes = [
        {"node_id": v, "status": str(d.rows[v].get("status")), "deps": d.below.get(v, [])}
        for v in d.statements
    ] + [{"node_id": j, "status": "route", "deps": d.below.get(j, [])} for j in d.junctions]
    lay = dag.layout(nodes, root=result.root, prefix=prefix, widths=widths)
    index = {s.id: k for k, s in enumerate(result.sets, start=1)}
    on_node, on_line = lit_sets(d, result)
    # F27-T8 (the owner): a statement's wedges are the sets whose plan uses it, as a leaf or as an
    # interior node the plan passes through; no separate mark says which, since the drawing does.
    members: dict[str, list[str]] = {}
    for s in result.sets:
        for m in dict.fromkeys((*s.statements, *s.assemblies)):
            members.setdefault(m, []).append(s.id)
    top = min((p.y for p in lay.placed), default=dag.PAD)
    sel_rows = selector_rows(result, d.rows, names, labels)
    column = selector_width(sel_rows)
    column_h = top + SEL_HEAD_H + len(sel_rows) * (SET_LABEL_H + SET_LABEL_GAP) + SEL_PAD
    width, height = lay.width + column, max(lay.height, round(column_h + dag.PAD))
    parts = [
        f'<svg class="routes-svg" viewBox="0 0 {width} {height}" width="{width}" '
        f'height="{height}" role="img" aria-label="routes and sufficient sets">',
        selector_box(sel_rows, column, top),
    ]
    # The tree sits right of the selector's column (F27-T7): every point moves by its width.
    lay = dag.Layout(
        [replace(p, x=p.x + column) for p in lay.placed],
        [replace(e, points=tuple((x + column, y) for x, y in e.points)) for e in lay.edges],
        width,
        height,
        lay.loose,
        lay.group_y,
    )
    for e in sorted(lay.edges, key=lambda e: (e.dst, e.src)):
        dead = any(x in d.junctions and not d.junctions[x].live for x in (e.src, e.dst))
        sets = " ".join(on_line.get((e.src, e.dst), []))
        parts.append(
            f'<path class="rline{" dead" if dead else ""}" data-from="{escape(e.src)}" '
            f'data-to="{escape(e.dst)}" data-sets="{escape(sets)}" d="{dag.path_d(e)}"/>'
        )
    for p in lay.placed:
        sets = escape(" ".join(on_node.get(p.node_id, [])))
        if p.node_id in d.junctions:
            parts.append(junction(d.junctions[p.node_id], p, sets))
            continue
        status = str(d.rows[p.node_id].get("status"))
        mine = members.get(p.node_id, [])
        role = "member" if mine else "none"
        said = ", ".join(f"set {index[s]}" for s in mine) if mine else "in no set"
        or_mark = (
            f'<path class="or-mark" d="M{p.w / 2:g} {dag.NODE_H - DIAMOND}'
            f'l{DIAMOND} {DIAMOND}l-{DIAMOND} {DIAMOND}l-{DIAMOND} -{DIAMOND}Z"/>'
            if d.alternatives.get(p.node_id, 0) >= 2
            else ""
        )
        label = dag.label_of(p.node_id, names, labels)
        named = f" ({escape(label)})" if p.node_id in labels else ""
        # Open is a second channel, never a hue: the wedges keep their colour and the pie is
        # hollow in the middle (proved is a full pie).
        core = (
            f'<circle class="core" cx="{PIE_X}" cy="{dag.NODE_H // 2}" r="{CORE_R}"/>'
            if mine and state_of(status) != "proved"
            else ""
        )
        root = " root" if p.node_id == result.root else ""
        # F28 (v3.41): a closable statement keeps its open look and gains the accent square; no
        # other statement carries a square (F27-T8: an interior node has no mark of its own).
        asm = ""
        joins = closable.get(p.node_id)
        if joins is not None:
            root += " closable"
            said += "; " + closable_words(joins, closable)
            asm = (
                f'<rect class="asm" x="{PIE_X - 3}" y="{dag.NODE_H // 2 - 3}" '
                'width="6" height="6"/>'
            )
        parts.append(
            f'<a href="{escape(href.get(p.node_id, "#"))}">'
            f'<g class="rnode st-{state_of(status)} {role}{root}" '
            f'data-node="{escape(p.node_id)}" '
            f'data-sets="{sets}" transform="translate({p.x},{p.y})">'
            f"<title>{escape(p.node_id)}{named}: {escape(status)}; {escape(said)}</title> "
            f'<rect class="pill" width="{p.w}" height="{dag.NODE_H}" rx="8"/>'
            f"{pie(mine, index)}{core}"
            f'<circle class="ring" cx="{PIE_X}" cy="{dag.NODE_H // 2}" r="{RING_R}"/>{asm}'
            f'<text x="{LABEL_X}" y="{dag.NODE_H // 2 + 5}">{escape(label)}</text> '
            f"{or_mark}</g></a>"
        )
    parts.append("</svg>")
    return "\n".join(parts)


@dataclass(frozen=True)
class SelRow:
    """One row of the selector box (F29-T6): a branch (an interior node of the tree, ``set``
    ``None``) or a leaf (one set, ``index`` its number from 1). ``sets`` are the ids of every
    set beneath it in the record's order; ``words`` the row's text (the statement the row's
    route is a route of and the route's approach; nothing at a leaf that chose no route); and
    ``title`` the full words for the row's ``<title>``."""

    depth: int
    sets: tuple[str, ...]
    set: str | None
    index: int
    words: str
    title: str


def _approach(rid: str, rows: Mapping[str, Mapping[str, Any]], label: str) -> str:
    """A route's approach (``graph/v12``, F29-R4): the declared line of its decomposition, else
    "route k of <label>"."""
    node_id, _, k = rid.rpartition("@")
    row = rows.get(node_id) or {}
    try:
        found = (row.get("decompositions") or [])[int(k) - 1].get("approach")
    except (IndexError, ValueError, AttributeError):
        found = None
    return str(found) if found else f"route {k} of {label}"


def _cut(text: str, width: int = SEL_TEXT_MAX) -> str:
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def selector_rows(
    result: routes.Routes,
    rows: Mapping[str, Mapping[str, Any]],
    names: dag.Prefix,
    labels: dag.Labels,
) -> list[SelRow]:
    """The selector tree flattened depth-first (R10). The top node is the box itself (its
    heading stands for every set); its children start at depth 0. A child's words name the
    statement its parent splits on (by its label) and the route it chose there, or that it took
    the statement directly; a leaf that is the top node (one set) has no words."""
    index = {s.id: k for k, s in enumerate(result.sets, start=1)}
    out: list[SelRow] = []

    def leaves(sel: routes.Selector) -> tuple[str, ...]:
        if sel.set is not None:
            return (sel.set,)
        return tuple(sid for c in sel.children for sid in leaves(c))

    def visit(sel: routes.Selector, split_on: str | None, depth: int) -> None:
        if split_on is None:
            words = full = ""
        else:
            label = dag.label_of(split_on, names, labels)
            if sel.route is None:
                words = full = f"{label}: taken directly"
            else:
                full = f"{label}: {_approach(sel.route, rows, label)}"
                words = _cut(full)
        beneath = leaves(sel)
        if sel.set is not None:
            k = index[sel.set]
            s = result.sets[k - 1]
            noun = "statement" if s.remaining == 1 else "statements"
            title = f"Set {k}: {s.remaining} open {noun} of {s.total}" + (
                f"; {full}" if full else ""
            )
            out.append(SelRow(depth, beneath, sel.set, k, words, title))
            return
        n = len(beneath)
        title = f"{full} ({n} set{'' if n == 1 else 's'})" if full else f"{n} sets"
        out.append(SelRow(depth, beneath, None, 0, words, title))
        for c in sel.children:
            visit(c, sel.node, depth + 1)

    tree = routes.selector_tree(result)
    if tree.sets == 0:
        return out
    if tree.set is not None:
        visit(tree, None, 0)
    else:
        for c in tree.children:
            visit(c, tree.node, 0)
    return out


def _row_w(r: SelRow) -> int:
    text = f"Set {r.index}" + (f"   {r.words}" if r.words else "") if r.set else r.words
    swatch = 18 if r.set else 0
    return r.depth * SEL_INDENT + 12 + swatch + round(SEL_CHAR_W * len(text)) + 12


def selector_width(sel_rows: list[SelRow]) -> int:
    """The column the box takes: its widest row, the heading, or F27-T7's least width."""
    widest = max((_row_w(r) for r in sel_rows), default=0)
    head = 12 + round(SEL_CHAR_W * len("Sufficient sets")) + 12
    return max(LABEL_COLUMN, widest + 2 * SEL_PAD + 8, head + 2 * SEL_PAD + 8)


def selector_box(sel_rows: list[SelRow], column: int, top: float) -> str:
    """F29-T6 (R10): the box headed "Sufficient sets", one row per node of the selector tree,
    each a button (``routes.js`` makes it select the sets beneath it) carrying ``data-sets``;
    a leaf keeps ``data-set`` and its hue as a swatch, as F27-T7's labels did. Complete and
    readable without the script."""
    box_w = column - 8 - SEL_PAD
    box_h = SEL_HEAD_H + len(sel_rows) * (SET_LABEL_H + SET_LABEL_GAP) + SEL_PAD
    y0 = round(top)
    out = [
        f'<g class="selector" transform="translate(8,{y0})">'
        f'<rect class="selector-box" width="{box_w}" height="{box_h}" rx="8"/>'
        f'<text class="selector-head" x="{SEL_PAD + 4}" y="18">Sufficient sets</text>'
    ]
    for i, r in enumerate(sel_rows):
        x = SEL_PAD + r.depth * SEL_INDENT
        y = SEL_HEAD_H + i * (SET_LABEL_H + SET_LABEL_GAP)
        w = box_w - x - SEL_PAD
        sets = escape(" ".join(r.sets))
        if r.set is not None:
            kind = "leaf set-label"
            own = f' data-set="{escape(r.set)}"'
            body = (
                f'<circle class="swatch {hue(r.index)}" cx="14" cy="{SET_LABEL_H // 2}" r="6"/>'
                f'<text x="26" y="{SET_LABEL_H // 2 + 5}">Set {r.index}</text>'
            )
            if r.words:
                wx = 26 + round(SEL_CHAR_W * len(f"Set {r.index}")) + 10
                body += (
                    f'<text class="sel-words" x="{wx}" y="{SET_LABEL_H // 2 + 5}">'
                    f"{escape(r.words)}</text>"
                )
        else:
            kind, own = "branch", ""
            body = f'<text x="10" y="{SET_LABEL_H // 2 + 5}">{escape(r.words)}</text>'
        out.append(
            f'<g class="sel-row {kind}"{own} data-sets="{sets}" role="button" tabindex="0" '
            f'aria-pressed="false" transform="translate({x},{y})">'
            f"<title>{escape(r.title)}</title>"
            f'<rect width="{w}" height="{SET_LABEL_H}" rx="6"/>{body}</g>'
        )
    out.append("</g>")
    return "".join(out)


def junction(r: routes.Route, p: dag.Placed, sets: str) -> str:
    """A route's junction: a stem through its box and a filled dot (AND); a route that closes
    nothing is a dashed ring with a cross."""
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
    return (
        f'<g class="junction {"live" if r.live else "dead"}" data-route="{escape(r.id)}" '
        f'data-node="{escape(r.id)}" data-sets="{sets}" transform="translate({p.x},{p.y})">'
        f"<title>{escape(words)}; from {escape(r.partial)}</title> "
        f'<path class="stem" d="M{cx} 0V{dag.NODE_H}"/>{mark}</g>'
    )


def _swatch(inner: str, w: int = 26) -> str:
    return (
        f'<svg class="routes-key-mark" width="{w}" height="22" viewBox="0 0 {w} 22" '
        f'aria-hidden="true">{inner}</svg>'
    )


def closable_words(c: closing.Closable, found: Mapping[str, closing.Closable]) -> str:
    """What a closable statement waits on: nothing but its own closing proof when it is ready,
    else the closable inputs whose closing proofs come first."""
    if c.ready:
        return "closable: its closing proof is pending"
    waiting = [i for i in c.link.inputs if i in found]
    return "closable once the closing proof of " + ", ".join(waiting) + " merges"


def closable_line(
    found: Mapping[str, closing.Closable],
    href: Mapping[str, str],
    prefix: str | None,
    root: str,
) -> str:
    """The closable statements named under the drawing, or nothing when there are none."""
    if not found:
        return ""
    names: dag.Prefix = (prefix, root) if prefix else None
    items = ", ".join(
        f'<a href="{escape(href.get(n, "#"))}">{escape(dag.label_of(n, names))}</a>' for n in found
    )
    return (
        f'<p class="routes-closable">Closable: {items}. Each one&rsquo;s proof exists in parts, '
        "its merged decomposition and the proofs of what it needs; nothing is proved until the "
        "closing proof that joins them passes the gate.</p>"
    )


def legend(result: routes.Routes) -> str:
    """The key, inside the drawing's card: every mark and every state the drawing can show."""
    c = 'cx="11" cy="11" r="7"'
    ring = 'cx="11" cy="11" r="9.5"'
    items = [
        (
            _swatch(
                '<path class="stem" d="M11 0V22"/><circle class="and-mark" cx="11" cy="11" r="5"/>'
            ),
            "route: all of its holes are needed (AND)",
        ),
        (
            _swatch('<path class="or-mark" d="M11 5l6 6l-6 6l-6 -6Z"/>'),
            "any one of the routes beneath closes it (OR)",
        ),
        (
            _swatch(
                '<path class="stem dead" d="M11 0V22"/><circle class="dead-mark" '
                'cx="11" cy="11" r="5"/><path class="dead-cross" d="M8 8l6 6m0 -6l-6 6"/>'
            ),
            "a route that closes nothing",
        ),
        (
            _swatch(f'<circle class="wedge set-1" {c}/><circle class="ring" {ring}/>'),
            "proved: full, solid ring",
        ),
        (
            _swatch(
                f'<g class="st-open"><circle class="wedge set-1" {c}/>'
                '<circle class="core" cx="11" cy="11" r="3"/>'
                f'<circle class="ring" {ring}/></g>'
            ),
            "open: hollow, dashed ring",
        ),
        (
            _swatch(f'<g class="st-dead"><circle class="ring" {ring}/></g>'),
            "refuted, defective, abandoned or superseded",
        ),
        (
            _swatch(
                f'<g class="st-open closable"><circle class="ring" {ring}/>'
                '<rect class="asm" x="8" y="8" width="6" height="6"/></g>'
            ),
            "closable: its proof exists in parts, the closing proof is pending",
        ),
        (
            _swatch(f'<g class="st-open"><circle class="ring" {ring}/></g>'),
            "in no set",
        ),
    ]
    more = (
        f" Sets beyond the {HUES}th are drawn grey; the table lists every one."
        if len(result.sets) > HUES
        else ""
    )
    body = "".join(f'<span class="routes-key-item">{mark}{words}</span>' for mark, words in items)
    return (
        f'<div class="routes-legend">{body}'
        f'<p class="routes-key-note">A statement&rsquo;s wedges are the sets whose plan uses '
        f"it, as a leaf or on the way to one, one colour per set as in the table.{more}</p></div>"
    )


def table(result: routes.Routes, prefix: str | None) -> str:
    """One row per set in the record's order (R11). Each count cell carries its number in
    ``data-sort``; the script adds the sorting and the toggle, which are rendered hidden."""
    names: dag.Prefix = (prefix, result.root) if prefix else None
    rows = []
    any_notes = any(s.variant for s in result.sets)
    for k, s in enumerate(result.sets, start=1):
        notes = []
        if s.variant:
            notes.append(
                f"goes through the variant <code>{escape(dag.label_of(s.variant, names))}</code>"
            )
        open_ids = "".join(
            f"<li><code>{escape(dag.label_of(m, names))}</code></li>" for m in s.open
        )
        proved_ids = "".join(
            f"<li><code>{escape(dag.label_of(m, names))}</code></li>" for m in s.proved
        )
        asm_ids = "".join(
            f"<li><code>{escape(dag.label_of(m, names))}</code></li>" for m in s.assemblies
        )
        listing = (
            '<details class="set-which"><summary>which</summary>'
            + (f"<p>Open</p><ul>{open_ids}</ul>" if open_ids else "")
            + (f"<p>Proved</p><ul>{proved_ids}</ul>" if proved_ids else "")
            + (f"<p>Assemblies</p><ul>{asm_ids}</ul>" if asm_ids else "")
            + "</details>"
        )
        cells = [
            f'<td data-sort="{k}"><span class="set-swatch {hue(k)}"></span>Set {k}{listing}</td>',
            f'<td class="num" data-sort="{s.total}">{s.total}</td>',
            f'<td class="num" data-sort="{s.closed}">{s.closed}</td>',
            f'<td class="num" data-sort="{s.remaining}">{s.remaining}</td>',
            f'<td class="num" data-sort="{s.shared}">{s.shared}</td>',
            f'<td class="num" data-sort="{len(s.assemblies)}">{len(s.assemblies)}</td>',
        ]
        if any_notes:
            cells.append(f"<td>{'; '.join(notes)}</td>")
        rows.append(
            f'<tr class="set-row" data-set="{escape(s.id)}" data-index="{k}" '
            f'data-remaining="{s.remaining}">' + "".join(cells) + "</tr>"
        )
    heads = [
        ("Set", "the sets in the record's order"),
        ("Statements", "statements in the set, proved and open"),
        ("Proved", "statements of the set already proved"),
        ("Open", "statements of the set still to prove"),
        ("Shared", "statements of the set that another set also holds"),
        ("Assemblies", "closing proofs of decomposed statements still to submit"),
        *([("Notes", "")] if any_notes else []),
    ]
    th = "".join(
        f'<th scope="col" data-col="{i}"' + (f' title="{escape(t)}"' if t else "") + f">{h}</th>"
        for i, (h, t) in enumerate(heads)
    )
    truncated = (
        '<p class="cue">The list was cut short at the enumeration&rsquo;s cap.</p>'
        if result.truncated
        else ""
    )
    count = len(result.sets)
    return (
        '<div class="routes-table-wrap">'
        f'<p class="routes-count">{count} sufficient set{"" if count == 1 else "s"}, in the '
        "record&rsquo;s order. "
        '<span class="routes-showing" hidden></span>'
        '<button type="button" class="routes-fewest" aria-pressed="false" hidden>'
        "Fewest open first</button></p>"
        f'<table class="routes-table"><thead><tr>{th}</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>{truncated}"
        '<p class="routes-hint" hidden>The first set comes selected. Select a set in the '
        "drawing&rsquo;s box, or its row, to light its statements and the lines up to the "
        "problem&rsquo;s own statement; a branch of the box selects every set beneath it, and "
        "the table shows the selected sets; select again, or press Escape, to clear.</p>"
        "</div>"
    )
