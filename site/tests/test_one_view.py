"""F30: one statement graph (the owner's request of 2026-10-18).

T1 (R6, R10; AC2, AC3, AC4): the views and their layouts. A view is a subset of the merged
graph (statements and route junctions) with the lines between them: ``all``, ``routes``, one per
selector node (the union of the sets beneath it), one per selector edge (the committed segment),
one per proof. Every view is laid out by ``dag.layout`` seeded with the full layout's order, so
statements shared by two views keep their left-to-right order.
"""

from __future__ import annotations

import functools
import json
import re
import socketserver
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from itertools import combinations
from pathlib import Path
from typing import Any

import fixture
import pytest
from harness import TARGET, copy_graph
from test_finding_dag_layout import crossings
from test_products import ROOT_NODE
from test_routes_view import Quiet, doc, nested_doc, node, render_tree, two_routes
from test_target_routes import live

from opn_gate import routes, scaffold
from opn_site import dag, one_view, render

T1 = "t@1"
T2 = "t@2"
A1 = "t--a@1"
A2 = "t--a@2"


def nested_views() -> dict[str, one_view.View]:
    g = nested_doc()
    return one_view.views(g, routes.read(g, []))


def trunk_doc() -> dict[str, Any]:
    """Root ``r`` with one route ``[x]`` and ``x`` split two ways, so the selector's top split is
    not the root: the trunk ``r → r@1 → x`` is common to both sets."""
    return {
        "schema": "graph/v12",
        "target_id": "r",
        "root": "r",
        "nodes": [
            node("r", origin="authored", routes=[["r--x"]], approaches=["down to x"]),
            node("r--x", routes=[["r--x--h1"], ["r--x--h2"]], approaches=["one", "two"]),
            node("r--x--h1"),
            node("r--x--h2"),
        ],
    }


# -- views: which nodes and lines ---------------------------------------------------------------


def test_layout_membership_per_view() -> None:
    """AC2: ``all`` holds every statement and junction, ``routes`` the on-route ones, a leaf its
    set's statements, assemblies and junctions, an interior node the union beneath it; every
    line of a view joins two nodes of it."""
    g = doc()
    vs = one_view.views(g, routes.read(g, []))
    assert set(vs["all"].nodes) == {
        "t",
        "t--a",
        "t--b",
        "t--c",
        "t--c--h1",
        "t--d",
        "v",
        "u",
        T1,
        T2,
        "t@3",
        "t--c@1",
    }
    # ``u`` is a related variant on no way to close the root; the dead route t@3 is drawn.
    assert set(vs["routes"].nodes) == set(vs["all"].nodes) - {"u"}
    assert vs["all"].kind == "all" and vs["routes"].kind == "routes"
    for v in vs.values():
        ids = set(v.nodes)
        for src, dst, _kind in v.lines:
            assert src in ids and dst in ids, (v.key, src, dst)

    nv = nested_views()
    leaf = nv[f"sel/{T1}/{A1}"]
    assert leaf.kind == "leaf" and len(leaf.sets) == 1
    assert set(leaf.nodes) == {"t", T1, "t--a", A1, "t--a--h1", "t--b"}
    assert set((s, d) for s, d, _k in leaf.lines) == {
        (T1, "t"),
        ("t--a", T1),
        ("t--b", T1),
        (A1, "t--a"),
        ("t--a--h1", A1),
    }
    branch = nv[f"sel/{T1}"]
    assert branch.kind == "node" and len(branch.sets) == 2
    assert set(branch.nodes) == set(leaf.nodes) | {A2, "t--a--h2"}
    top = nv["sel"]
    assert set(top.nodes) == set(branch.nodes) | {T2, "t--c"} and len(top.sets) == 3
    assert set(nv.keys()) >= {
        "all",
        "routes",
        "sel",
        f"sel/{T1}",
        f"sel/{T1}/{A1}",
        f"sel/{T1}/{A2}",
        f"sel/{T2}",
        f"edge/sel/{T1}",
        f"edge/sel/{T1}/{A1}",
        f"edge/sel/{T1}/{A2}",
        f"edge/sel/{T2}",
    }


def test_an_edge_view_is_the_committed_part_between_two_forks() -> None:
    """AC3 (Q3): the edge "close t by route t@1" runs from t through the junction to what every
    set beneath shares — ``b``, a hole that leads to no further choice, is committed too — and
    stops at ``a``, the next fork, inclusive; the edge into a leaf runs to the set's bottom."""
    nv = nested_views()
    seg = nv[f"edge/sel/{T1}"]
    assert seg.kind == "edge"
    assert set(seg.nodes) == {"t", T1, "t--a", "t--b"}
    assert set((s, d) for s, d, _k in seg.lines) == {(T1, "t"), ("t--a", T1), ("t--b", T1)}
    assert set(seg.sets) == set(nv[f"sel/{T1}"].sets)
    to_leaf = nv[f"edge/sel/{T1}/{A1}"]
    assert set(to_leaf.nodes) == {"t--a", A1, "t--a--h1"}
    other = nv[f"edge/sel/{T2}"]
    assert set(other.nodes) == {"t", T2, "t--c"}


def test_the_trunk_edge_runs_from_the_root_to_the_first_split() -> None:
    """AC3: when the top split is not the root, the trunk edge's segment is root to that split."""
    g = trunk_doc()
    vs = one_view.views(g, routes.read(g, []))
    assert set(vs["edge/sel"].nodes) == {"r", "r@1", "r--x"}
    assert set(vs["sel"].nodes) == {"r", "r@1", "r--x", "r--x@1", "r--x@2", "r--x--h1", "r--x--h2"}
    assert "edge/sel" not in nested_views(), "the top split is the root: no trunk edge"


def test_a_proof_is_a_view_of_its_closure() -> None:
    """AC7 (Q4): a proof's view is its closure with the edges its term follows."""
    g = doc()
    marks = [dag.ProofMarks(nodes=frozenset({"t", "t--b"}), edges=frozenset({("t--b", "t")}))]
    vs = one_view.views(g, routes.read(g, []), proofs=marks)
    assert vs["proof/0"].kind == "proof"
    assert set(vs["proof/0"].nodes) == {"t", "t--b"}
    assert [(s, d) for s, d, _k in vs["proof/0"].lines] == [("t--b", "t")]


# -- layouts: tidy, and still -------------------------------------------------------------------


def all_layouts(g: dict[str, Any]) -> dict[str, dag.Layout]:
    result = routes.read(g, [])
    vs = one_view.views(g, result)
    return one_view.layouts(g["nodes"], vs, root=str(g["root"]), prefix=str(g["target_id"]))


@pytest.mark.parametrize("make", [doc, nested_doc, trunk_doc])
def test_every_view_is_a_tidy_layout(make: Any) -> None:
    """AC4: no overlap; each node one layer below the lowest node that rests on it; a view's
    layout holds exactly the view's nodes."""
    g = make()
    vs = one_view.views(g, routes.read(g, []))
    for key, lay in all_layouts(g).items():
        assert {p.node_id for p in lay.placed} == set(vs[key].nodes), key
        for a, b in combinations(lay.placed, 2):
            if a.y == b.y:
                assert a.x + a.w <= b.x or b.x + b.w <= a.x, (key, a, b)
        layer = {p.node_id: p.layer for p in lay.placed}
        above: dict[str, list[str]] = {}
        for e in lay.edges:
            above.setdefault(e.src, []).append(e.dst)
        for src, dsts in above.items():
            assert min(layer[d] for d in dsts) == layer[src] + 1, (key, src, dsts)


def order_disagreements(lays: dict[str, dag.Layout]) -> list[tuple[str, str, str, str]]:
    """Pairs of statements on one row in two views whose left-to-right order differs."""
    out = []
    for (ka, la), (kb, lb) in combinations(lays.items(), 2):
        at_a = {p.node_id: p for p in la.placed}
        at_b = {p.node_id: p for p in lb.placed}
        shared = sorted(set(at_a) & set(at_b))
        for u, v in combinations(shared, 2):
            if at_a[u].y != at_a[v].y or at_b[u].y != at_b[v].y:
                continue
            if (at_a[u].x < at_a[v].x) != (at_b[u].x < at_b[v].x):
                out.append((ka, kb, u, v))
    return out


@pytest.mark.parametrize("make", [doc, nested_doc, trunk_doc])
def test_shared_statements_keep_their_order_across_views(make: Any) -> None:
    """AC4 (R10, Q2): across every pair of views, statements on one row in both keep their order."""
    assert order_disagreements(all_layouts(make())) == []


def test_shared_statements_keep_their_order_on_live_erdos_1094(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R10 on the live shape: a view departs from the shared order only where keeping it would
    cross a line in that view (shown by laying the view out with the seed's order pinned, no
    sweeps, and counting its crossings). Without the seed the live shape has 191 such pairs."""
    graph, entries = live("erdos-1094")
    result = routes.read(graph, entries)
    vs = one_view.views(graph, result)
    lays = one_view.layouts(graph["nodes"], vs, root=str(graph["root"]), prefix="erdos-1094")
    assert len(result.sets) >= 2 and len(lays) > len(result.sets)
    seed = one_view.order_seed(lays["all"])
    status = one_view.statuses(graph["nodes"])
    widths = one_view.junction_widths(vs["all"], status)
    departed = order_disagreements(lays)
    assert len(departed) <= 2, departed
    monkeypatch.setattr(dag, "ORDER_SWEEPS", 0)
    for ka, kb, _u, _v in departed:
        pinned = [
            one_view.layout_view(
                vs[k],
                status,
                root=str(graph["root"]),
                prefix="erdos-1094",
                widths=widths,
                labels=None,
                order=seed,
            )
            for k in (ka, kb)
            if k != "all"
        ]
        assert any(crossings(lay) for lay in pinned), (ka, kb)


def test_the_seed_orders_siblings_when_nothing_else_does() -> None:
    """Q2: ``dag.layout`` takes an ``order`` seed (each node's x in a reference layout); two
    siblings that nothing distinguishes come out in the seed's order, so a subset view keeps the
    full view's order."""
    nodes: list[dict[str, Any]] = [
        {"node_id": "r", "status": "ready", "deps": ["a", "b", "c"]},
        {"node_id": "a", "status": "ready", "deps": []},
        {"node_id": "b", "status": "ready", "deps": []},
        {"node_id": "c", "status": "ready", "deps": []},
    ]
    forward = dag.layout(nodes, order={"a": 0.0, "b": 100.0, "c": 200.0})
    backward = dag.layout(nodes, order={"a": 200.0, "b": 100.0, "c": 0.0})
    x_f = {p.node_id: p.x for p in forward.placed}
    x_b = {p.node_id: p.x for p in backward.placed}
    assert x_f["a"] < x_f["b"] < x_f["c"]
    assert x_b["c"] < x_b["b"] < x_b["a"]


# -- the embedded document ----------------------------------------------------------------------


def test_the_layouts_document_carries_each_view(tmp_path: Path) -> None:
    """R6: one entry per view with the drawing's size, each node's x, y and width and each
    line's bend points; ids and numbers only, no words; the live target stays small."""
    graph, entries = live("erdos-1094")
    vs = one_view.views(graph, routes.read(graph, entries))
    lays = one_view.layouts(graph["nodes"], vs, root=str(graph["root"]), prefix="erdos-1094")
    document = one_view.layouts_document(lays)
    text = json.dumps(document, separators=(",", ":"))
    parsed = json.loads(text)
    assert set(parsed) == set(vs)
    for key, entry in parsed.items():
        assert set(entry) >= {"w", "h", "nodes", "lines"}, key
        assert set(entry["nodes"]) == set(vs[key].nodes)
        for _nid, (x, y, w) in entry["nodes"].items():
            assert all(isinstance(v, (int, float)) for v in (x, y, w))
        for src, dst, kind, pts in entry["lines"]:
            assert src in entry["nodes"] and dst in entry["nodes"] and isinstance(kind, str)
            assert len(pts) >= 2 and all(len(p) == 2 for p in pts)
    (tmp_path / "size.txt").write_text(f"{len(text)}\n")
    assert len(text) < 400_000, len(text)


# -- T3: the page in a browser (R3, R7, R8; AC5 to AC8) -----------------------------------------
#
# Playwright: ``uv run --frozen --with playwright pytest site/tests/test_one_view.py``. The
# browser tests skip without it, which proves nothing, so the evidence runs them.

LEAF = "svg.selector g.sel-node.kind-leaf"
SEL_EDGE = "svg.selector path.sel-edge"
VARIANT = "variant-related"


def off_route(tmp_path: Path) -> Path:
    """``two_routes`` plus a ``related`` variant: on no way to close the root, so it is in ``all``
    and not in ``routes`` and the view-toggle is rendered (R4)."""
    root = two_routes(tmp_path)
    proposal = scaffold.Proposal(
        node_id=VARIANT,
        target_id=TARGET,
        statement="theorem OpnProp.variant_related : ∀ p : Prop, p → p := by\n  sorry\n",
        witness="theorem witness : True := trivial\n",
        author="proposer",
        origin="variant",
        relation="related",
        date="2026-10-01T00:00:00Z",
    )
    scaffold.validate(proposal)
    scaffold.write(fixture.nodes_dir(root), proposal)
    return root


def embedded_layouts(page: str) -> dict[str, Any]:
    m = re.search(r'<script type="application/json" id="graph-layouts">(.*?)</script>', page, re.S)
    assert m is not None, "no #graph-layouts"
    parsed: dict[str, Any] = json.loads(m.group(1))
    return parsed


def dag_markup(page: str) -> str:
    start = page.index('<svg class="dag"')
    return page[start : page.index("</svg>", start)]


def test_complete_without_the_script(tmp_path: Path) -> None:
    """AC8 (R11): read without JavaScript, the page shows the ``routes`` layout at its own
    coordinates, the selector and the full table; every pill is a link; the buttons the script
    needs are rendered hidden; no element is positioned by script (every position is a
    ``transform`` attribute in the markup, none a style)."""
    page = render_tree(two_routes(tmp_path))[f"problems/{TARGET}/index.html"]
    assert '<script src="/graph.js"></script>' in page
    assert "/problem.js" not in page and "/routes.js" not in page
    drawing = dag_markup(page)
    assert 'class="dag" data-view="routes"' in drawing
    lays = embedded_layouts(page)
    assert {"all", "routes"} <= set(lays)
    # Every statement drawn is a link, at the routes layout's coordinates.
    pills = re.findall(r'<a href="([^"]+)"><g class="node[^"]*" data-node="([^"]+)"', drawing)
    assert len(pills) == drawing.count('<g class="node')
    assert len(pills) == drawing.count("data-node=") - drawing.count('<g class="junction')
    for g in re.finditer(
        r'<g class="(?P<cls>[^"]*)" data-node="(?P<id>[^"]+)"[^>]*'
        r'transform="translate\((?P<x>[-\d.]+),(?P<y>[-\d.]+)\)"',
        drawing,
    ):
        at = lays["routes"]["nodes"].get(g["id"])
        if "off-view" in g["cls"]:
            assert at is None, g["id"]
            continue
        assert at is not None, g["id"]
        assert (float(g["x"]), float(g["y"])) == pytest.approx(at[:2], abs=0.01), g["id"]
    assert 'style="transform' not in page and 'style="translate' not in page
    # The selector and the whole table, the rows carrying their views.
    assert '<svg class="selector"' in page
    rows = re.findall(r'<tr class="set-row"[^>]*>', page)
    assert len(rows) == 2 and all("hidden" not in r and 'data-view="' in r for r in rows)
    for sel in ("dag-toggle", "view-toggle", "routes-fewest"):
        for tag in re.findall(rf'<button[^>]*class="[^"]*\b{sel}\b[^"]*"[^>]*>', page):
            assert "hidden" in tag, tag


def test_a_proof_is_a_leaf_of_the_selector(tmp_path: Path) -> None:
    """AC7 (Q4): a target with a proof has a proof leaf whose view is the proof's closure, and
    its note is rendered hidden for the script to show."""
    page = render_tree(copy_graph(tmp_path, publish=True))[f"problems/{TARGET}/index.html"]
    leaf = re.search(r'<g class="sel-node kind-proof"[^>]*data-view="proof/0"', page)
    assert leaf is not None
    lays = embedded_layouts(page)
    assert "proof/0" in lays and ROOT_NODE in lays["proof/0"]["nodes"]
    note = re.search(r'<p class="proof-note"[^>]*data-view="proof/0"[^>]*>', page)
    assert note is not None and "hidden" in note.group(0)
    assert "proof-picker" not in page


#: Every node's box, translate, display and lit state; every line's ``d`` and state; the svg's
#: view and size; the open panel; the pressed selector elements; the table's shown rows.
SNAPSHOT = """() => {
  const svg = document.querySelector('svg.dag');
  const vis = el => getComputedStyle(el).display !== 'none';
  const out = {
    view: svg.getAttribute('data-view'), viewBox: svg.getAttribute('viewBox'),
    width: svg.getAttribute('width'), height: svg.getAttribute('height'),
    hash: location.hash, picking: svg.classList.contains('picking'),
    hovering: svg.classList.contains('hovering'), nodes: {}, edges: {},
    panel: [...document.querySelectorAll('.panel[data-node]')].filter(p => !p.hidden)
      .map(p => p.getAttribute('data-node')),
    pressed: [...document.querySelectorAll('svg.selector [aria-pressed="true"]')]
      .map(e => e.getAttribute('data-view')),
    rows: [...document.querySelectorAll('tr.set-row')].filter(r => !r.hidden)
      .map(r => r.getAttribute('data-view')),
    showing: (document.querySelector('.routes-showing') || {textContent: ''}).textContent,
    toggle: (b => b ? b.getAttribute('aria-pressed') : null)(
      document.querySelector('button.view-toggle')),
  };
  svg.querySelectorAll('[data-node]').forEach(g => {
    const r = g.getBoundingClientRect();
    const m = /translate\\(([-\\d.]+),([-\\d.]+)\\)/.exec(g.getAttribute('transform') || '');
    out.nodes[g.getAttribute('data-node')] = {
      box: [r.x, r.y, r.width, r.height], at: m ? [parseFloat(m[1]), parseFloat(m[2])] : null,
      shown: vis(g), lit: g.classList.contains('lit'),
      opacity: parseFloat(getComputedStyle(g).opacity),
    };
  });
  svg.querySelectorAll('path.edge').forEach(e => {
    out.edges[e.getAttribute('data-key')] = {
      d: e.getAttribute('d'), shown: vis(e), lit: e.classList.contains('lit'),
      opacity: parseFloat(getComputedStyle(e).opacity),
    };
  });
  return out;
}"""


@contextmanager
def browser(root: Path, out: Path, *, reduced: bool = True) -> Iterator[Any]:
    """The rendered site served locally and the problem page open in Chromium."""
    sync_api = pytest.importorskip("playwright.sync_api")
    render.write(render_tree(root), out)
    handler = functools.partial(Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1440, "height": 900})
            if reduced:
                pg.emulate_media(reduced_motion="reduce")
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/")
            pg.wait_for_load_state("networkidle")
            pg.locator(".statements-section").scroll_into_view_if_needed()
            try:
                yield pg
            finally:
                b.close()


def layouts_in(pg: Any) -> dict[str, Any]:
    found: dict[str, Any] = pg.evaluate(
        "() => JSON.parse(document.getElementById('graph-layouts').textContent)"
    )
    return found


def shown_nodes(snap: dict[str, Any]) -> set[str]:
    return {i for i, n in snap["nodes"].items() if n["shown"]}


def shown_edges(snap: dict[str, Any]) -> set[str]:
    return {k for k, e in snap["edges"].items() if e["shown"]}


def lit_nodes(snap: dict[str, Any]) -> set[str]:
    return {i for i, n in snap["nodes"].items() if n["lit"]}


def lit_edges(snap: dict[str, Any]) -> set[str]:
    return {k for k, e in snap["edges"].items() if e["lit"]}


def boxes(snap: dict[str, Any]) -> dict[str, list[float]]:
    return {i: n["box"] for i, n in snap["nodes"].items()}


def numbers(d: str) -> list[float]:
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", d)]


def line_keys(lay: dict[str, Any]) -> set[str]:
    return {f"{s}>{d}" for s, d, _k, _p in lay["lines"]}


def assert_at_layout(snap: dict[str, Any], lay: dict[str, Any]) -> None:
    """The drawing shows exactly the layout's nodes and lines, each at the layout's place, its
    lines drawn as ``dag.path_d`` draws them, and the svg sized to the layout."""
    assert shown_nodes(snap) == set(lay["nodes"])
    for nid, (x, y, _w) in lay["nodes"].items():
        assert snap["nodes"][nid]["at"] == pytest.approx([x, y], abs=0.01), nid
    assert shown_edges(snap) == line_keys(lay)
    for s, d, kind, pts in lay["lines"]:
        edge = dag.Edge(src=s, dst=d, kind=kind, points=tuple((x, y) for x, y in pts))
        want = numbers(dag.path_d(edge))
        assert numbers(snap["edges"][f"{s}>{d}"]["d"]) == pytest.approx(want, abs=0.2), (s, d)
    assert numbers(snap["viewBox"]) == pytest.approx([0, 0, lay["w"], lay["h"]], abs=0.01)
    assert float(snap["width"]) == pytest.approx(lay["w"], abs=0.01)
    assert float(snap["height"]) == pytest.approx(lay["h"], abs=0.01)


def unquoted(hash_: str) -> str:
    return hash_.replace("%2F", "/").replace("%40", "@").replace("%3A", ":")


def test_selecting_a_leaf_an_edge_and_clearing_moves_the_drawing(tmp_path: Path) -> None:  # noqa: PLR0915 — one browser session, each state it passes through
    """AC5 (R7): a leaf click leaves only its view's nodes at the view's coordinates and the
    hash carries the view; an edge click leaves the segment; the pressed element again, or
    Escape, restores ``routes``; the panel never changes; the table filters to the view's sets;
    "Fewest open first" selects the first row's view. Then, without reduced motion, the same
    leaf click arrives at the same place through the three phases."""
    with browser(two_routes(tmp_path / "g"), tmp_path / "site") as pg:
        lays = layouts_in(pg)
        loaded = pg.evaluate(SNAPSHOT)
        leaves = pg.locator(LEAF)
        leaf_key = leaves.nth(0).get_attribute("data-view")
        other_key = leaves.nth(1).get_attribute("data-view")
        edge_key = pg.locator(SEL_EDGE).nth(1).get_attribute("data-view")
        assert leaf_key and other_key and edge_key
        assert {leaf_key, other_key, edge_key} <= set(lays)
        leaves.nth(0).click()
        pg.mouse.move(5, 5)
        on_leaf = pg.evaluate(SNAPSHOT)
        pg.locator(SEL_EDGE).nth(1).click()
        pg.mouse.move(5, 5)
        on_edge = pg.evaluate(SNAPSHOT)
        pg.locator(SEL_EDGE).nth(1).click()
        pg.mouse.move(5, 5)
        cleared = pg.evaluate(SNAPSHOT)
        leaves.nth(1).click()
        pg.mouse.move(5, 5)
        on_second = pg.evaluate(SNAPSHOT)
        pg.keyboard.press("Escape")
        escaped = pg.evaluate(SNAPSHOT)
        fewest = pg.locator("button.routes-fewest")
        assert fewest.is_visible()
        fewest.click()
        pg.mouse.move(5, 5)
        first_row_view = pg.locator("tr.set-row").nth(0).get_attribute("data-view")
        by_fewest = pg.evaluate(SNAPSHOT)
        fewest_pressed = fewest.get_attribute("aria-pressed")
    with browser(two_routes(tmp_path / "g2"), tmp_path / "site2", reduced=False) as pg:
        pg.locator(LEAF).nth(0).click()
        pg.mouse.move(5, 5)
        mid = pg.evaluate(SNAPSHOT)
        pg.wait_for_function(
            "v => document.querySelector('svg.dag').getAttribute('data-view') === v",
            arg=leaf_key,
            timeout=5000,
        )
        animated = pg.evaluate(SNAPSHOT)
    assert loaded["view"] == "routes" and loaded["hash"] == ""
    assert_at_layout(loaded, lays["routes"])
    assert on_leaf["view"] == leaf_key
    assert_at_layout(on_leaf, lays[leaf_key])
    assert f"view={leaf_key}" in unquoted(on_leaf["hash"])
    assert on_leaf["pressed"] == [leaf_key]
    assert on_leaf["panel"] == loaded["panel"] == [ROOT_NODE]
    assert on_leaf["rows"] == [leaf_key] and on_leaf["showing"] == "showing 1 of 2"
    assert on_edge["view"] == edge_key
    assert_at_layout(on_edge, lays[edge_key])
    assert on_edge["pressed"] == [edge_key] and on_edge["panel"] == loaded["panel"]
    assert cleared["view"] == "routes" and cleared["pressed"] == []
    assert "view=" not in cleared["hash"]
    assert_at_layout(cleared, lays["routes"])
    assert len(cleared["rows"]) == 2 and cleared["showing"] == ""
    assert on_second["view"] == other_key and on_second["pressed"] == [other_key]
    assert escaped["view"] == "routes" and escaped["pressed"] == []
    assert_at_layout(escaped, lays["routes"])
    assert fewest_pressed == "true" and first_row_view and by_fewest["view"] == first_row_view
    assert_at_layout(by_fewest, lays[first_row_view])
    # Without reduced motion the drawing is still moving right after the click (the svg has not
    # taken the view yet) and arrives at the same place.
    assert mid["view"] != leaf_key
    assert animated["view"] == leaf_key
    assert_at_layout(animated, lays[leaf_key])


def test_hover_previews_without_moving(tmp_path: Path) -> None:
    """AC6 (R8): hovering a selector node, an edge or a table row lights that view's nodes and
    lines and dims the rest; no node moves and the view does not change; leaving restores the
    selection's state."""
    with browser(two_routes(tmp_path / "g"), tmp_path / "site") as pg:
        lays = layouts_in(pg)
        loaded = pg.evaluate(SNAPSHOT)
        leaf_key = pg.locator(LEAF).nth(0).get_attribute("data-view")
        edge_key = pg.locator(SEL_EDGE).nth(1).get_attribute("data-view")
        row_key = pg.locator("tr.set-row").nth(1).get_attribute("data-view")
        assert leaf_key and edge_key and row_key
        pg.locator(LEAF).nth(0).hover()
        on_leaf = pg.evaluate(SNAPSHOT)
        pg.locator(SEL_EDGE).nth(1).hover()
        on_edge = pg.evaluate(SNAPSHOT)
        pg.locator("tr.set-row").nth(1).hover()
        on_row = pg.evaluate(SNAPSHOT)
        pg.mouse.move(5, 5)
        left = pg.evaluate(SNAPSHOT)
        # With a leaf selected, hovering the other leaf previews over the selection's layout and
        # leaving restores it.
        pg.locator(LEAF).nth(0).click()
        pg.mouse.move(5, 5)
        selected = pg.evaluate(SNAPSHOT)
        pg.locator(LEAF).nth(1).hover()
        over = pg.evaluate(SNAPSHOT)
        pg.mouse.move(5, 5)
        back = pg.evaluate(SNAPSHOT)
    for snap, key in ((on_leaf, leaf_key), (on_edge, edge_key), (on_row, row_key)):
        assert snap["view"] == "routes" and snap["picking"], key
        assert boxes(snap) == boxes(loaded), "a node moved"
        assert lit_nodes(snap) == set(lays[key]["nodes"]), key
        assert lit_edges(snap) == line_keys(lays[key]), key
        dimmed = {i for i, n in snap["nodes"].items() if n["shown"] and n["opacity"] < 0.9}
        assert dimmed == set(lays["routes"]["nodes"]) - set(lays[key]["nodes"]), key
    assert not left["picking"] and lit_nodes(left) == set() and boxes(left) == boxes(loaded)
    assert selected["view"] == leaf_key and not selected["picking"]
    assert over["view"] == leaf_key and over["picking"]
    assert boxes(over) == boxes(selected) and shown_nodes(over) == shown_nodes(selected)
    assert back["view"] == leaf_key and not back["picking"] and boxes(back) == boxes(selected)


def test_a_pill_click_opens_the_panel_and_moves_nothing(tmp_path: Path) -> None:
    """AC6 (R3): hovering a pill lights its lines and the statements they join and moves
    nothing; clicking a pill shows its panel, writes ``#node=`` and moves nothing — and never
    changes the view."""
    hole = f"{ROOT_NODE}--h1"
    with browser(two_routes(tmp_path / "g"), tmp_path / "site") as pg:
        lays = layouts_in(pg)
        loaded = pg.evaluate(SNAPSHOT)
        pg.locator(f'svg.dag g.node[data-node="{ROOT_NODE}"]').hover()
        hovered = pg.evaluate(SNAPSHOT)
        pg.mouse.move(5, 5)
        pg.locator(f'svg.dag g.node[data-node="{hole}"]').click()
        pg.mouse.move(5, 5)
        clicked = pg.evaluate(SNAPSHOT)
        href = pg.locator(f'svg.dag a:has(> g.node[data-node="{hole}"])').get_attribute("href")
    assert loaded["panel"] == [ROOT_NODE]
    assert hovered["hovering"] and not hovered["picking"]
    touching = {f"{s}>{d}" for s, d, _k, _p in lays["routes"]["lines"] if ROOT_NODE in (s, d)}
    assert lit_edges(hovered) == touching
    assert ROOT_NODE in lit_nodes(hovered) and len(lit_nodes(hovered)) > 1
    assert boxes(hovered) == boxes(loaded)
    assert clicked["panel"] == [hole]
    assert clicked["hash"] == f"#node={hole}"
    assert clicked["view"] == "routes" and not clicked["picking"]
    assert boxes(clicked) == boxes(loaded)
    assert href and href != "#" and href.endswith("/")  # still a link to the record page


def test_the_toggle_shows_every_statement(tmp_path: Path) -> None:
    """AC7 (R4): the toggle, hidden without the script, shows the ``all`` layout with the
    off-route statements at their coordinates and names how many it adds; pressing it again
    returns to ``routes``; pressing it while a leaf is selected clears the selection."""
    with browser(off_route(tmp_path / "g"), tmp_path / "site") as pg:
        lays = layouts_in(pg)
        loaded = pg.evaluate(SNAPSHOT)
        toggle = pg.locator("button.view-toggle")
        assert toggle.is_visible()
        label = toggle.text_content()
        toggle.click()
        pg.mouse.move(5, 5)
        on_all = pg.evaluate(SNAPSHOT)
        all_label = toggle.text_content()
        toggle.click()
        pg.mouse.move(5, 5)
        back = pg.evaluate(SNAPSHOT)
        pg.locator(LEAF).nth(0).click()
        pg.mouse.move(5, 5)
        on_leaf = pg.evaluate(SNAPSHOT)
        toggle.click()
        pg.mouse.move(5, 5)
        from_leaf = pg.evaluate(SNAPSHOT)
    assert VARIANT in lays["all"]["nodes"] and VARIANT not in lays["routes"]["nodes"]
    assert loaded["toggle"] == "false" and VARIANT not in shown_nodes(loaded)
    assert label and "1" in label
    assert on_all["view"] == "all" and on_all["toggle"] == "true"
    assert_at_layout(on_all, lays["all"])
    assert "view=all" in on_all["hash"]
    assert all_label != label
    assert back["view"] == "routes" and back["toggle"] == "false"
    assert_at_layout(back, lays["routes"])
    assert on_leaf["toggle"] == "false" and on_leaf["pressed"]
    assert from_leaf["view"] == "all" and from_leaf["pressed"] == []
    assert from_leaf["toggle"] == "true"
