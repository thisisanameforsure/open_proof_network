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

import re
from collections.abc import Callable, Mapping, Sequence
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


def retire_controls(
    s: routes.SufficientSet,
    route_rows: Mapping[str, RouteRow],
    target_id: str,
    name_of: Callable[[str], str],
) -> str:
    """F34-T46 (ROUND-2 D3): the retire controls of the route Figure 1 draws, one per split the
    route goes through, each named by its words — the statement split and the split's approach —
    never by a raw id. A split already cut says what shelving did to it. ``shelve.js`` fills a
    control for a steward or curator; the stylesheet shows a split's words only beside a filled
    control or a shelving, so every other reader sees nothing here."""
    parts = []
    for rid in s.routes:
        r = route_rows.get(rid)
        if r is None:
            continue
        words = f"Split of {name_of(r.node)}" + (f": {cut(r.approach, 60)}" if r.approach else "")
        if r.cut:
            tail = f' <span class="route-state">{escape(r.shelving)}</span>' if r.shelving else ""
        else:
            tail = (
                f'<span class="retire-act" data-target="{escape(target_id)}" '
                f'data-node="{escape(r.node)}" data-partial="{escape(r.partial)}" hidden></span>'
            )
        if not tail:
            continue
        title = f' title="{escape(r.approach)}"' if r.approach else ""
        parts.append(
            f'<span class="set-route"{title}><span class="split-words">{escape(words)}</span>'
            f"{tail}</span>"
        )
    return "".join(parts)


#: A partial's file name carries who wrote it: ``attempts/<stamp>Z-<who>-partial.lean``.
_PARTIAL_BY = re.compile(r"\d{8}T\d{6}Z-(.+?)-partial")
SIDE_ROW_WORDS = {PROVES: "proves the problem", routes.REFUTES: "would disprove it"}


def split_by(partial: str) -> str | None:
    """Who wrote a route's split, from its partial's file name; ``None`` when it names nobody."""
    m = _PARTIAL_BY.search(partial)
    return m.group(1) if m else None


@dataclass(frozen=True)
class RouteFacts:
    """F34-T47: what a route's row says beyond its set — the view its number draws, its name
    (the picker's, "Route n · <approach>"), and the statement boxes its drawing holds, in all and
    proved (F34-T46: the count is the drawing's)."""

    view: str
    name: str
    drawn: int
    proved: int


def _statement_links(
    title: str, members: Sequence[str], name_of: Callable[[str], str], href: Mapping[str, str]
) -> str:
    if not members:
        return ""
    items = "".join(
        f'<li><a href="{escape(href.get(m, "#"))}">{escape(name_of(m))}</a></li>' for m in members
    )
    return f"<p>{title}</p><ul>{items}</ul>"


def route_list(  # noqa: PLR0913 — the list's inputs
    result: routes.Routes,
    facts: Mapping[str, RouteFacts],
    *,
    route_rows: Mapping[str, RouteRow],
    name_of: Callable[[str], str],
    href: Mapping[str, str],
    home: str = "",
    controls: bool = False,
    harder: frozenset[str] = frozenset(),
) -> str:
    """F34-T47 (ROUND-2 D1; mockup ``New-Erdos257-List``; the owner, 2026-11-27: "Drop the table.
    Keep what is shown in the problems design."): one row per route, in the picker's order — its
    number in a circle, its name, which way it settles the problem and its counts, the statement
    it goes through and who split it, and Draw, Statements and (a steward's or curator's, on a
    build with a service) Retire. ``facts`` is keyed by set id; a set with no numbered end has no
    row. ``harder`` (D2): the ids of the strictly harder sets, listed after the others under their
    own subheading. The row of ``home`` is rendered marked; graph.js moves the mark."""
    main: list[str] = []
    more: list[str] = []
    for k, s in enumerate(result.sets, start=1):
        f = facts.get(s.id)
        if f is None:
            continue
        side = settles(s)
        _head, _, gist = f.name.partition(" · ")
        name = gist[:1].upper() + gist[1:] if gist else f.name
        split = max(f.drawn - f.proved - s.remaining, 0)
        noun = "statement" if f.drawn == 1 else "statements"
        counts = (
            f"{SIDE_ROW_WORDS.get(side, side)} · {f.drawn} {noun} · {f.proved} proved · "
            + (
                '<span title="statements this route splits into the others">'
                f"{split} split further</span> · "
                if split
                else ""
            )
            + f"<strong>{s.remaining} open</strong>"
        )
        first = route_rows.get(s.routes[0]) if s.routes else None
        through_id = s.variant or (first.node if first is not None else result.root)
        label = name_of(through_id)
        through = f"through <code>{escape(through_id)}</code>" + (
            f" ({escape(label)})" if through_id not in (result.root, label) else ""
        )
        who = split_by(first.partial) if first is not None else None
        if who:
            through += f", split by <code>{escape(who)}</code>"
        elif first is None:
            through += ", taken directly"
        listing = (
            '<details class="route-statements"><summary>Statements</summary>'
            + _statement_links("Open", s.open, name_of, href)
            + _statement_links("Proved", s.proved, name_of, href)
            + _statement_links("Split further", s.assemblies, name_of, href)
            + "</details>"
        )
        retire = (
            '<details class="route-retire"><summary>Retire…</summary>'
            f"{retire_controls(s, route_rows, result.target_id, name_of)}</details>"
            if controls
            else ""
        )
        on = f.view == home
        row = (
            f'<li class="route-row side-{escape(side)}" data-set="{escape(s.id)}" '
            f'data-index="{k}" data-view="{escape(f.view)}" '
            f'aria-selected="{"true" if on else "false"}"'
            + (' data-harder="true"' if s.id in harder else "")
            + ">"
            f'<button type="button" class="route-n" aria-pressed="{"true" if on else "false"}" '
            f'aria-label="Draw route {k}">{k}</button>'
            '<div class="route-body">'
            f'<span class="route-name">{escape(name)}</span>'
            f'<span class="route-counts">{counts}</span>'
            f'<span class="route-through">{through}</span>'
            '<span class="route-acts"><a href="#proof" class="route-draw">Draw</a>'
            f"{listing}{retire}</span>"
            "</div></li><!-- /route-row -->"
        )
        (more if s.id in harder else main).append(row)
    if not main and not more:
        return ""
    truncated = (
        '<p class="cue">The list was cut short at the enumeration&rsquo;s cap.</p>'
        if result.truncated
        else ""
    )
    harder_block = (
        '<div class="harder-routes" hidden><h4 class="harder-head">Harder routes</h4>'
        f'<ol class="route-list">{"".join(more)}</ol></div>'
        if more
        else ""
    )
    return (
        '<div class="route-list-wrap">'
        f'<ol class="route-list">{"".join(main)}</ol>{harder_block}{truncated}</div>'
    )
