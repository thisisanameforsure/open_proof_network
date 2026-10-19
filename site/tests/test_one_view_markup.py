"""F30-T2 (R1, R2, R4, R5, R9, R11; AC1, AC7, AC8): the merged drawing's markup.

One ``svg.dag`` with the statements and the route junctions, proved as a filled pill, the key
naming every mark, the selector drawn as nodes and edges, the sets table below the drawing, the
layouts embedded as JSON, and no Routes section or proof buttons left on the page.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET, copy_graph
from test_decompositions import HOLE_IDS
from test_one_view import followed_doc, trunk_doc
from test_products import ROOT_NODE
from test_proof_selector import erdos_shape
from test_routes_view import THIRD, doc, nested_doc, render_tree, two_routes
from test_target_proofs import resolves_variant

from opn_gate import routes
from opn_site import one_view, render

PAGE = f"problems/{TARGET}/index.html"


def drawing_of(page: str) -> str:
    start = page.index('<svg class="dag"')
    return page[start : page.index("</svg>", start)]


def g_of(svg: str, node_id: str) -> str:
    m = re.search(rf'<g class="[^"]*" data-node="{re.escape(node_id)}"[^>]*>.*?</g>', svg, re.S)
    assert m is not None, node_id
    return m.group(0)


def classes_of(svg: str, node_id: str) -> set[str]:
    m = re.search(rf'<g class="([^"]*)" data-node="{re.escape(node_id)}"', svg)
    assert m is not None, node_id
    return set(m.group(1).split())


def layouts_in(page: str) -> dict[str, dict[str, Any]]:
    m = re.search(r'<script type="application/json" id="graph-layouts">(.*?)</script>', page, re.S)
    assert m is not None, "no embedded layouts"
    parsed: dict[str, dict[str, Any]] = json.loads(m.group(1))
    return parsed


# -- AC1: one drawing ---------------------------------------------------------------------------


def test_one_drawing_with_junctions_and_no_routes_section(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path))[PAGE]
    assert page.count('<svg class="dag"') == 1
    for gone in ("routes-section", "routes-svg", "proof-picker", "/routes.js", "/problem.js"):
        assert gone not in page, gone
    assert '<script src="/graph.js"></script>' in page
    svg = drawing_of(page)
    assert svg.count('<g class="junction live"') == 2 and 'class="or-mark"' in g_of(svg, ROOT_NODE)
    assert 'data-view="routes"' in svg[: svg.index(">")]
    # T7: the selector sits in the drawing's card above the drawing; the table below the grid.
    assert page.index('<div class="graph-grid">') < page.index('<div class="sets-grid">')
    assert page.index('<svg class="selector"') < page.index('<svg class="dag"')
    assert page.count('<tr class="set-row"') == 2
    for row in re.findall(r'<tr class="set-row"[^>]*>', page):
        assert 'data-view="sel' in row, row
    lays = layouts_in(page)
    assert {"all", "routes", "sel"} <= set(lays)
    assert set(lays["routes"]["nodes"]) >= {ROOT_NODE, *HOLE_IDS, THIRD}


def test_every_line_of_every_view_is_drawn_once_and_off_route_ones_are_hidden() -> None:
    """R11, R4: the markup holds the union of the views' nodes and lines; what the opening
    (routes) layout does not show carries ``off-view``; ``u`` is on no route."""
    g = doc()
    d = one_view.drawing(g, [], href={n["node_id"]: "#" for n in g["nodes"]}, prefix="t")
    svg = d.svg
    assert "off-view" in classes_of(svg, "u") and "off-view" not in classes_of(svg, "t--a")
    keys = [html.unescape(k) for k in re.findall(r'data-key="([^"]+)"', svg)]
    assert len(keys) == len(set(keys))
    vs = one_view.views(g, routes.read(g, []))
    want = {f"{s}>{t}" for v in vs.values() for s, t, _k in v.lines}
    assert set(keys) == want
    assert d.toggle and "1 more" in d.toggle and 'data-view="all"' in d.toggle


def test_no_toggle_when_every_statement_is_on_a_route() -> None:
    g = nested_doc()
    d = one_view.drawing(g, [], href={n["node_id"]: "#" for n in g["nodes"]}, prefix="t")
    assert d.toggle == ""


# -- AC1: proved is the filled pill; the key -----------------------------------------------------


def test_proved_is_the_filled_pill(tmp_path: Path) -> None:
    page = render_tree(erdos_shape(tmp_path))[PAGE]
    svg = drawing_of(page)
    assert "proved" in classes_of(svg, ROOT_NODE) and "status-proved" in classes_of(svg, ROOT_NODE)
    assert "proved" not in classes_of(svg, "and-reassoc")
    for stale in ("on-proof", "off-proof", "data-proofs", "data-sets", 'class="wedge'):
        assert stale not in svg, stale


def test_the_key_names_the_route_marks_when_the_drawing_has_them(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path))[PAGE]
    key = re.search(r'<div class="dag-legend">(.*?)</div>', page, re.S)
    assert key is not None
    assert "all of its holes" in key.group(1) and "any one" in key.group(1)
    plain = render_tree(copy_graph(tmp_path / "plain", publish=True))[PAGE]
    key2 = re.search(r'<div class="dag-legend">(.*?)</div>', plain, re.S)
    assert key2 is not None and "all of its holes" not in key2.group(1)
    assert "on this proof" not in key.group(1) and "not needed by this proof" not in page


# -- R5: the selector as nodes and edges --------------------------------------------------------


def test_the_selector_is_nodes_and_edges_keyed_by_view() -> None:
    g = nested_doc()
    d = one_view.drawing(g, [], href={n["node_id"]: "#" for n in g["nodes"]}, prefix="t")
    sel = d.selector
    nodes = re.findall(r'<g class="sel-node ([a-z-]+)"[^>]*data-view="([^"]*)"', sel)
    assert ("kind-node", "sel") in nodes and ("kind-node", "sel/t@1") in nodes
    assert ("kind-leaf", "sel/t@2") in nodes and ("kind-leaf", "sel/t@1/t--a@1") in nodes
    edges = re.findall(r'<path class="sel-edge"[^>]*data-view="([^"]*)"', sel)
    assert set(edges) == {
        "edge/sel/t@1",
        "edge/sel/t@2",
        "edge/sel/t@1/t--a@1",
        "edge/sel/t@1/t--a@2",
    }
    assert "edge/sel" not in edges, "the top split is the root: no trunk edge"
    # Every selector element names the sets beneath it; a leaf names one.
    m = re.search(r'data-view="sel/t@2"[^>]*data-sets="([^"]*)"', sel) or re.search(
        r'data-sets="([^"]*)"[^>]*data-view="sel/t@2"', sel
    )
    assert m is not None and len(m.group(1).split()) == 1
    assert "Split at the conjunction" in sel  # the route's approach labels its edge
    assert 'role="button"' in sel and 'tabindex="0"' in sel


def test_the_root_tops_the_selector_when_the_first_split_is_lower() -> None:
    g = trunk_doc()
    d = one_view.drawing(g, [], href={n["node_id"]: "#" for n in g["nodes"]}, prefix="r")
    assert '<g class="sel-node kind-root"' in d.selector
    assert 'data-view="edge/sel"' in d.selector and 'data-from="root"' in d.selector


def test_a_proof_is_a_leaf_of_the_selector(tmp_path: Path) -> None:
    """AC7 (Q4): a proved target's proofs hang from the selector as leaves, with the proof note
    beneath, keyed by view; two proofs are two leaves in record order."""
    root = erdos_shape(tmp_path)
    resolves_variant(root, "variant-later", 9, "carol")
    page = render_tree(root)[PAGE]
    sel = page[page.index('<svg class="selector"') :]
    sel = sel[: sel.index("</svg>")]
    leaves = re.findall(r'<g class="sel-node kind-proof"[^>]*data-view="(proof/\d)"', sel)
    assert leaves == ["proof/0", "proof/1"]
    assert re.search(r'<p class="proof-note" data-view="proof/0"[^>]*>', page)
    lays = layouts_in(page)
    assert set(lays["proof/0"]["nodes"]) == {ROOT_NODE, "tutorial-and-swap"}


def test_the_follow_toggle_sits_in_the_selector_panel_with_both_counts(tmp_path: Path) -> None:
    """F27-AC14 (R13): the "Stop at proved statements" toggle is rendered once, inside the
    selector's panel, ticked and hidden (only the script can act on it); every set view has its
    ``follow/`` twin among the layouts; each count the reading changes carries both numbers in
    the cell, and the proved list both lists."""
    page = render_tree(two_routes(tmp_path))[PAGE]
    head = page.index('<div class="selector-wrap">')
    wrap = page[head : page.index('<svg class="selector"', head)]
    assert re.search(
        r'<label class="sel-follow" title="[^"]+" hidden>'
        r'<input type="checkbox" class="follow-proved" checked> Stop at proved statements</label>',
        wrap,
    )
    assert page.count('class="sel-follow"') == 1
    lays = layouts_in(page)
    set_keys = [k for k in lays if k == "sel" or k.startswith(("sel/", "edge/"))]
    assert set_keys and all(one_view.FOLLOW + k in lays for k in set_keys)
    both = re.findall(
        r'<td class="num" data-sort="(\d+)" data-sort-follow="(\d+)">'
        r'<span class="v-stop">\1</span><span class="v-follow">\2</span></td>',
        page,
    )
    assert len(both) == 3 * page.count('<tr class="set-row"')  # Statements, Proved, Shared
    # On a document whose proofs rest on something, the second reading differs.
    d = one_view.drawing(followed_doc(), [], href={})
    assert d.follow_toggle.startswith('<label class="sel-follow"')
    assert 'data-sort="2" data-sort-follow="3"' in d.table  # set 1's statements: a, p (+ p--h1)
    assert 'data-sort="1" data-sort-follow="3"' in d.table  # set 2's statements: q (+ both holes)
    assert '<ul class="v-follow"><li><code>' in d.table


# -- AC8: complete without the script -----------------------------------------------------------


def test_complete_without_the_script(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path))[PAGE]
    svg = drawing_of(page)
    for nid in (ROOT_NODE, *HOLE_IDS, THIRD):
        assert re.search(rf'<a href="/[^"]+"><g class="node [^"]*" data-node="{nid}"', svg), nid
        assert "off-view" not in classes_of(svg, nid)
    assert 'class="chip view-toggle"' not in page or " hidden>" in page
    assert page.count("<table") == 1
    assert (
        '<span class="routes-showing" hidden>' in page
    )  # the filter's count line waits for the script
    assert 'class="routes-fewest" aria-pressed="false" hidden>' in page


@pytest.mark.parametrize("make", [doc, nested_doc])
def test_the_markup_escapes_ids_and_words(make: object) -> None:
    g = make()  # type: ignore[operator]
    g["nodes"][0]["label"] = '<b>&"'
    g["nodes"][0]["label_source"] = "gloss"
    d = one_view.drawing(g, [], href={n["node_id"]: "#" for n in g["nodes"]}, prefix="t")
    assert "<b>" not in d.svg and "&lt;b&gt;" in d.svg
    assert "<b>" not in d.selector


# -- T7 (the owner, 2026-10-18): the selector is a small tree at the top of the drawing's card ----


def test_the_selector_is_a_small_tree_above_the_drawing(tmp_path: Path) -> None:
    """The selector sits in the drawing's card before the drawing, is a compact tree (dots and
    straight lines, no pills, no visible words), and every node carries its words for the hover."""
    page = render_tree(two_routes(tmp_path))[PAGE]
    card = page.index('<div class="dag-wrap card">')
    assert card < page.index('<svg class="selector"') < page.index('<svg class="dag"')
    assert "sets-grid" not in page or page.index("sets-grid") > page.index(
        "</svg>", page.index('<svg class="dag"')
    )
    sel = page[page.index('<svg class="selector"') :]
    sel = sel[: sel.index("</svg>")]
    head = sel[: sel.index(">")]
    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head)
    assert m is not None
    assert float(m.group(1)) <= 160 and float(m.group(2)) <= 140, head  # two leaves, two rows
    assert 'class="pill"' not in sel and "sel-approach" not in sel
    nodes = re.findall(r'<g class="sel-node [^"]*"[^>]*>', sel)
    assert nodes and all('data-words="' in n for n in nodes), nodes
    # T10 (the owner): a fork is a small square and the root a dashed square, never a circle,
    # which the drawing below uses for a statement; a set keeps its numbered circle.
    for part in re.findall(r'<g class="sel-node .*?</g>', sel, re.S):
        if "kind-leaf" in part or "kind-proof" in part:
            assert '<circle class="dot"' in part, part
        else:
            assert '<rect class="dot"' in part and "<circle" not in part, part
    assert sel.count('class="sel-edge"') == 2
    for e in re.findall(r'<path class="sel-edge"[^>]*d="([^"]+)"', sel):
        assert "C" not in e and "Q" not in e, e  # straight lines, a typical tree


def test_selector_leaves_are_numbered_in_record_order_under_their_parents() -> None:
    g = nested_doc()
    d = one_view.drawing(g, [], href={n["node_id"]: "#" for n in g["nodes"]}, prefix="t")
    leaves = re.findall(
        r'<g class="sel-node kind-leaf"[^>]*transform="translate\(([\d.]+),([\d.]+)\)"[^>]*>'
        r".*?<text[^>]*>(\d)</text>",
        d.selector,
        re.S,
    )
    assert [n for _x, _y, n in leaves] == ["1", "2", "3"]
    xs = [float(x) for x, _y, _n in leaves]
    assert xs == sorted(xs) and len(set(xs)) == 3
    # Sets 1 and 2 are siblings under t@1 and share a row; their parent sits one row above,
    # centred over them; Set 3 hangs from the top directly, so it is a row higher (a typical
    # tree, leaves at their own depths).
    ys = [float(y) for _x, y, _n in leaves]
    assert ys[0] == ys[1] and ys[2] < ys[0]
    parent = re.search(
        r'<g class="sel-node kind-node"[^>]*data-view="sel/t@1"[^>]*'
        r'transform="translate\(([\d.]+),([\d.]+)\)"',
        d.selector,
    )
    assert parent is not None
    px, py = float(parent.group(1)), float(parent.group(2))
    assert py < ys[0] and py == ys[2]
    assert abs(px - (xs[0] + xs[1]) / 2) < 0.6


def test_the_selector_says_it_is_the_navigation_and_explains_a_sufficient_set(
    tmp_path: Path,
) -> None:
    """T9 (the owner, 2026-10-18): a short line tells the reader to select a node or an edge to
    filter the drawing, and the heading's words carry a hover card defining a sufficient set."""
    page = render_tree(two_routes(tmp_path))[PAGE]
    wrap = page[page.index('<div class="selector-wrap">') : page.index('<svg class="selector"')]
    assert "Select a node or an edge" in wrap and "filter" in wrap.lower()
    assert 'class="term' in wrap and "sufficient set" in wrap.lower()
    assert render.esc(render.GLOSSARY_BY_KEY["sufficient-set"][1]) in wrap
    assert (
        "sufficient-set" in render.GLOSSARY_BY_KEY
        and "sufficient set" in render.GLOSSARY_BY_KEY["sufficient-set"][0]
    )


def test_a_selected_selector_mark_is_amber_not_the_accent() -> None:
    """T10 (the owner): the pressed node or edge wears a colour of its own (amber), so a
    selection is told apart from the accent the hover and the drawing use."""
    css = (Path(render.__file__).resolve().parent / "static" / "site.css").read_text()
    assert "--select:" in css
    pressed = [
        ln
        for ln in css.splitlines()
        if 'aria-pressed="true"' in ln and ".selector" in ln and " text " not in ln
    ]
    assert len(pressed) == 2 and all("var(--select)" in ln for ln in pressed), pressed
    assert "var(--accent)" not in " ".join(pressed)
