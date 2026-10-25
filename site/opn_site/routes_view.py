"""The routes' facts for the problem page (F27-T3; R11; D-25 v3.40, D-36), read by ``one_view``.

A target read as an AND-OR graph, drawn from ``opn_gate.routes`` over the same two products the
MCP tool reads (``graph.json`` and the target's ``frontier.json`` entries), so the page and the
tool cannot disagree (F27-Q1).

F30 (2026-10-18) folded the routes drawing and its selector box into the page's one statement
graph (``opn_site.one_view``); what stays here is what that drawing reads: ``drawn`` (every
statement on a way to close the root and the junction of each route), the sets table, a route's
approach words and the closable words.

F29-T6 (R10; D-25 v3.44): the selector tree (``routes.selector_tree``, built from the sets) is
boxed as "Sufficient sets" down the drawing's left edge, where F27-T7's set labels stood: one row
per node of the tree in depth-first order, indented by depth, a branch naming the statement its
route is a route of and the route's approach, a leaf one set with its swatch. Every row carries
in ``data-sets`` the sets beneath it, so the script lights a branch as it lights a set.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
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
#: The ring (solid when proved, dashed when open) sits just outside the pie, so a dashed ring
#: never cuts into a set's colour.
#: An open statement's pie is hollow to this radius.
#: Room for the label after its text (the box is ``LABEL_X`` + the text + this).
DIAMOND = 6
#: F27-T7: the column down the drawing's left edge that holds the selector (F29-T6, where one
#: label per set stood); the statements and lines are drawn to its right, so no row covers one.
#: This is its least width; the box grows to its longest row (``selector_width``).
SET_LABEL_W = 80
#: F29-T6: the selector's rows — indented this much per depth, the words in the sans face at
#: about this width a character, cut at this many characters (the whole text stays in the
#: row's ``<title>``), under a heading this tall, inside a box with this much padding.
SEL_TEXT_MAX = 40
DEAD = routes.DEAD_STATUSES


@dataclass
class Drawn:
    """The graph the drawing lays out: statements and junctions, each with what it is drawn
    above, and per element the sets it belongs to."""

    rows: dict[str, Mapping[str, Any]]
    statements: list[str] = field(default_factory=list)
    junctions: dict[str, routes.Route] = field(default_factory=dict)
    below: dict[str, list[str]] = field(default_factory=dict)
    alternatives: dict[str, int] = field(default_factory=dict)
    #: F30-T11: the band's statements (proposed cruxes and their holes), visited as the root is,
    #: so their routes have junctions too; never on a way to close the root.
    band: list[str] = field(default_factory=list)


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


#: The relation labels drawn as a trunk from the variant into the root (D-30 v3.46): a proved
#: one settles the root, each its own way.
#: F30-T16 (the owner, 2026-10-22): a partial variant has a kernel-checked relation too, so it
#: is connected to the root by its own line; a related variant has none and lives in the column.
TRUNK_LABELS = (routes.RESOLVES, routes.REFUTES, "partial")


def drawn(graph: Mapping[str, Any], result: routes.Routes) -> Drawn:
    """Every statement on a way to close the root: through routes' holes (live or dead, so a
    dead route is seen), through declared non-hole dependencies, and at the root through each
    ``resolves`` or (v3.46) ``refutes`` variant. A line that would return to a statement on its
    own path is not drawn (the enumeration drops such a route too, F27-R5). F30-T11: the band's
    cruxes (``dag.proposed``) are visited the same way into ``band``, so their routes have
    junctions, after the root's walk; a band statement the root's walk reached is the tree's."""
    rows = {str(n["node_id"]): n for n in graph.get("nodes") or [] if isinstance(n, Mapping)}
    out = Drawn(rows)
    if result.root not in rows:
        return out
    by_node: dict[str, list[routes.Route]] = {}
    for r in result.routes:
        by_node.setdefault(r.node, []).append(r)
    variants = [
        k for k, row in rows.items() if k != result.root and row.get("relation") in TRUNK_LABELS
    ]
    seen: set[str] = set()

    def visit(node_id: str, path: tuple[str, ...], sink: list[str]) -> None:
        if node_id in seen:
            return
        seen.add(node_id)
        sink.append(node_id)
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
                    visit(str(h.node), here, sink)
        for dep in plain_deps(node_id, rows, held):
            if dep not in here:
                below.append(dep)
                visit(dep, here, sink)
        alts = len([j for j in below if j in out.junctions])
        if node_id == result.root:
            for v in variants:
                if v not in here:
                    below.append(v)
                    alts += 1
                    visit(v, here, sink)
        out.below[node_id] = below
        out.alternatives[node_id] = alts

    visit(result.root, (), out.statements)
    # the column's heads (F30-T16): their routes need junctions too; one the root reached is skipped
    for crux in [*dag.speculative(rows.values()), *dag.related_variants(rows.values())]:
        visit(crux, (), out.band)
    return out


#: D-25 v3.46: which way a set settles the root, as ``routes`` publishes it (F27-T11).
PROVES = routes.PROVES
SIDE_WORDS = {PROVES: "proves the problem", routes.REFUTES: "refutes the problem"}


def settles(s: routes.SufficientSet) -> str:
    """The side the set settles: ``routes.SufficientSet.settles``."""
    return s.settles


def side_of(sel: routes.Selector) -> str | None:
    """The side a selector node carries (v3.46: set on the two children of a top fork whose
    ``node`` is ``None``), or ``None``: ``routes.Selector.side``."""
    return sel.side


def hue(k: int) -> str:
    """The class of the ``k``-th set (from 1): its own hue up to ``HUES``, grey beyond."""
    return f"set-{k}" if k <= HUES else "set-more"


def _num(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def approach_of(rid: str, rows: Mapping[str, Mapping[str, Any]], label: str) -> str:
    """A route's approach (``graph/v12``, F29-R4): the declared line of its decomposition, else
    "route k of <label>"."""
    node_id, _, k = rid.rpartition("@")
    row = rows.get(node_id) or {}
    try:
        found = (row.get("decompositions") or [])[int(k) - 1].get("approach")
    except (IndexError, ValueError, AttributeError):
        found = None
    return str(found) if found else f"route {k} of {label}"


def cut(text: str, width: int = SEL_TEXT_MAX) -> str:
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def closable_words(c: closing.Closable, found: Mapping[str, closing.Closable]) -> str:
    """What a closable statement waits on: nothing but its own closing proof when it is ready,
    else the closable inputs whose closing proofs come first."""
    if c.ready:
        return "closable: its closing proof is pending"
    waiting = [i for i in c.link.inputs if i in found]
    return "closable once the closing proof of " + ", ".join(waiting) + " merges"


def _ids(members: Sequence[str], names: dag.Prefix) -> str:
    return "".join(f"<li><code>{escape(dag.label_of(m, names))}</code></li>" for m in members)


def _count(stop: int, follow: int | None) -> str:
    """A count cell: its number in ``data-sort``; with a followed reading (F27-R13) that number
    too, in ``data-sort-follow`` and a second span the stylesheet shows in its place."""
    if follow is None:
        return f'<td class="num" data-sort="{stop}">{stop}</td>'
    return (
        f'<td class="num" data-sort="{stop}" data-sort-follow="{follow}">'
        f'<span class="v-stop">{stop}</span><span class="v-follow">{follow}</span></td>'
    )


@dataclass(frozen=True)
class RouteRow:
    """F31-T11 (R8): one drawn route as the sets table names it — its id (``<node>@<k>``), the
    statement it decomposes, the partial's file (what a retirement names, ``shelving/v1``
    ``route``), its approach, and what shelving did to it (``None`` when nothing; see
    ``one_view.shelving_words``)."""

    id: str
    node: str
    partial: str
    approach: str | None
    shelving: str | None
    #: Every hole of it is shelved (retired, or shelved one by one): nothing is left to retire.
    cut: bool = False


def route_cell(
    s: routes.SufficientSet, route_rows: Mapping[str, RouteRow], target_id: str, *, controls: bool
) -> str:
    """F31-Q18 (the owner, 2026-10-25): the routes a set goes through, each named in the row
    with its approach as the title and, with a service, its hidden ``.retire-act`` control
    (``shelve.js`` shows Retire to a steward or curator) unless the route is already cut, in
    which case what shelving did to it is said instead."""
    parts = []
    for rid in s.routes:
        r = route_rows.get(rid)
        if r is None:
            parts.append(
                f'<span class="set-route" data-route="{escape(rid)}">'
                f"<code>{escape(rid)}</code></span>"
            )
            continue
        if r.cut or not controls:
            tail = f' <span class="route-state">{escape(r.shelving)}</span>' if r.shelving else ""
        else:
            tail = (
                f'<span class="retire-act" data-target="{escape(target_id)}" '
                f'data-node="{escape(r.node)}" data-partial="{escape(r.partial)}" hidden></span>'
            )
        title = f' title="{escape(r.approach)}"' if r.approach else ""
        parts.append(
            f'<span class="set-route" data-route="{escape(rid)}"{title}><code>{escape(rid)}</code>'
            f"{tail}</span>"
        )
    return f'<td class="set-routes" data-sort="{len(s.routes)}">{"".join(parts)}</td>'


def table(  # noqa: PLR0913 — the table's inputs
    result: routes.Routes,
    prefix: str | None,
    views: Mapping[str, str] | None = None,
    follow: routes.Routes | None = None,
    *,
    route_rows: Mapping[str, RouteRow] | None = None,
    controls: bool = False,
) -> str:
    """One row per set in the record's order (R11). Each count cell carries its number in
    ``data-sort``; the script adds the sorting and the toggle, which are rendered hidden.
    ``follow`` (F27-R13), the same sets read past their proved statements, gives each row its
    second reading: the statement, proved and shared counts and the list of proved statements
    under ``v-follow``, shown when the page's toggle is unticked. ``route_rows`` (F31-Q18) adds
    a Routes column naming the routes each set goes through, with the retire control when
    ``controls`` (a build with a service address)."""
    names: dag.Prefix = (prefix, result.root) if prefix else None
    rows = []
    any_notes = any(s.variant for s in result.sets)
    twin = {s.id: s for s in follow.sets} if follow is not None else {}
    for k, s in enumerate(result.sets, start=1):
        f = twin.get(s.id)
        side = settles(s)
        notes = []
        if s.variant:
            notes.append(
                f"goes through the variant <code>{escape(dag.label_of(s.variant, names))}</code>"
            )
        open_ids = _ids(s.open, names)
        proved_ids = _ids(s.proved, names)
        asm_ids = _ids(s.assemblies, names)
        if f is None:
            proved_list = f"<p>Proved</p><ul>{proved_ids}</ul>" if proved_ids else ""
        else:
            proved_list = (
                f'<p>Proved</p><ul class="v-stop">{proved_ids}</ul>' if proved_ids else ""
            ) + f'<ul class="v-follow">{_ids(f.proved, names)}</ul>'
        listing = (
            '<details class="set-which"><summary>which</summary>'
            + (f"<p>Open</p><ul>{open_ids}</ul>" if open_ids else "")
            + proved_list
            + (f"<p>Assemblies</p><ul>{asm_ids}</ul>" if asm_ids else "")
            + "</details>"
        )
        # F04-T55 (D-25 v3.46): a refuting set says so beside its number.
        word = f' <span class="set-side">{escape(side)}</span>' if side != PROVES else ""
        cells = [
            f'<td data-sort="{k}"><span class="set-swatch {hue(k)}"></span>Set {k}{word}'
            f"{listing}</td>",
            _count(s.total, f.total if f else None),
            _count(s.closed, f.closed if f else None),
            f'<td class="num" data-sort="{s.remaining}">{s.remaining}</td>',
            _count(s.shared, f.shared if f else None),
            f'<td class="num" data-sort="{len(s.assemblies)}">{len(s.assemblies)}</td>',
        ]
        if route_rows is not None:
            cells.append(route_cell(s, route_rows, result.target_id, controls=controls))
        if any_notes:
            cells.append(f"<td>{'; '.join(notes)}</td>")
        rows.append(
            f'<tr class="set-row side-{escape(side)}" data-set="{escape(s.id)}" data-index="{k}" '
            f'data-remaining="{s.remaining}"'
            + (f' data-view="{escape(views[s.id])}"' if views and s.id in views else "")
            + ">"
            + "".join(cells)
            + "</tr>"
        )
    heads = [
        ("Set", "the sets in the record's order"),
        ("Statements", "statements in the set, proved and open"),
        ("Proved", "statements of the set already proved"),
        ("Open", "statements of the set still to prove"),
        ("Shared", "statements of the set that another set also holds"),
        ("Assemblies", "closing proofs of decomposed statements still to submit"),
        *(
            [
                (
                    "Routes",
                    "the merged decompositions the set goes through; a steward or curator "
                    "may retire one",
                )
            ]
            if route_rows is not None
            else []
        ),
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
        f'<p class="routes-count">{count} way{"" if count == 1 else "s"} to settle the '
        "problem, in the record&rsquo;s order. "
        '<span class="routes-showing" hidden></span>'
        '<button type="button" class="routes-fewest" aria-pressed="false" hidden>'
        "Fewest open first</button></p>"
        f'<table class="routes-table"><thead><tr>{th}</tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>{truncated}"
        '<p class="routes-hint" hidden>Hover a set, a branch or an edge of the tree, or a row, to '
        "light what it holds on the drawing; select it and the drawing becomes that tree. A "
        "branch is every set beneath it, an edge the part a route choice commits to. The table "
        "shows the selected sets; select again, or press Escape, to come back.</p>"
        "</div>"
    )
