"""F30: one statement graph (the owner's request of 2026-10-18).

T1 (R6, R10; AC2, AC3, AC4): the views and their layouts. A view is a subset of the merged
graph (statements and route junctions) with the lines between them: ``all``, ``routes``, one per
selector node (the union of the sets beneath it), one per selector edge (the committed segment),
one per proof. Every view is laid out by ``dag.layout`` seeded with the full layout's order, so
statements shared by two views keep their left-to-right order.
"""

from __future__ import annotations

import functools
import http.server
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
import samples
import yaml
from harness import TARGET
from test_decompositions import HOLE_IDS
from test_finding_dag_layout import crossings
from test_products import ROOT_NODE, nodes_dir
from test_products import attest as gate_attest
from test_routes_view import REPO, THIRD, doc, nested_doc, node, render_tree, two_routes
from test_target_routes import live

from opn_gate import products, routes, scaffold
from opn_site import dag, model, one_view, render

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


def with_proof(row: dict[str, Any], used: list[str]) -> dict[str, Any]:
    """The row with one merged proof whose term ``used`` these nodes (graph/v4's ``proofs``)."""
    row["proofs"] = [
        {
            "kind": "proof",
            "path": "Proof.lean",
            "artifact_hash": "0" * 64,
            "attestation": "000001.json",
            "merge_commit": "0" * 40,
            "submitter": None,
            "used": used,
        }
    ]
    return row


def followed_doc() -> dict[str, Any]:
    """F27-R13: root ``t`` with two routes, ``[a, p]`` and ``[q]``. ``p`` is proved past its
    route (its term used ``p--h1`` alone, as a lemma); ``q`` is proved as its route's assembly
    (its term used both holes). The published sets are ``{a, p}`` and ``{q}``; followed, they
    also hold ``p--h1`` and ``q--h1, q--h2``."""
    return {
        "schema": "graph/v12",
        "target_id": "t",
        "root": "t",
        "nodes": [
            node(
                "t",
                origin="authored",
                routes=[["t--a", "t--p"], ["t--q"]],
                approaches=["through p", "through q"],
            ),
            node("t--a"),
            with_proof(node("t--p", "proved", routes=[["t--p--h1", "t--p--h2"]]), ["t--p--h1"]),
            with_proof(node("t--p--h1", "proved"), []),
            with_proof(node("t--p--h2", "proved"), []),
            with_proof(
                node("t--q", "proved", routes=[["t--q--h1", "t--q--h2"]]),
                ["t--q--h1", "t--q--h2"],
            ),
            with_proof(node("t--q--h1", "proved"), []),
            with_proof(node("t--q--h2", "proved"), []),
        ],
    }


# -- views: which nodes and lines ---------------------------------------------------------------


def test_follow_views_add_what_proved_members_rest_on() -> None:
    """F27-AC14 (R13): every set view has a ``follow/`` twin — the same kind, sets, split, route
    and index, its parent the twin of its parent — whose nodes add what each proved statement's
    proof rests on: a proof that went past its route adds the hole it used and the direct line
    it took, no junction; a proof that is its route's assembly adds the route's junction and
    both holes. The plain views are untouched."""
    g = followed_doc()
    stop = routes.read(g, [])
    follow = routes.read(g, [], at_proved="follow")
    plain = one_view.views(g, stop)
    vs = one_view.views(g, stop, follow=follow)
    assert {k: v for k, v in vs.items() if not k.startswith(one_view.FOLLOW)} == plain
    set_keys = [k for k in plain if k == "sel" or k.startswith(("sel/", "edge/"))]
    assert set_keys
    assert sum(1 for k in vs if k.startswith(one_view.FOLLOW)) == len(set_keys)
    for k in set_keys:
        a, b = vs[k], vs[one_view.FOLLOW + k]
        assert (b.kind, b.sets, b.route, b.split, b.index) == (
            a.kind,
            a.sets,
            a.route,
            a.split,
            a.index,
        )
        assert b.parent == (one_view.FOLLOW + a.parent if a.parent else None)
        assert set(a.nodes) <= set(b.nodes)
    assert set(vs["sel/t@1"].nodes) == {"t", "t@1", "t--a", "t--p"}
    past = vs[one_view.FOLLOW + "sel/t@1"]
    assert set(past.nodes) == {"t", "t@1", "t--a", "t--p", "t--p--h1"}
    assert ("t--p--h1", "t--p", "edge") in past.lines
    assert set(vs["sel/t@2"].nodes) == {"t", "t@2", "t--q"}
    assembly = vs[one_view.FOLLOW + "sel/t@2"]
    assert set(assembly.nodes) == {"t", "t@2", "t--q", "t--q@1", "t--q--h1", "t--q--h2"}
    assert {(src, dst) for src, dst, _k in assembly.lines} >= {
        ("t--q@1", "t--q"),
        ("t--q--h1", "t--q@1"),
        ("t--q--h2", "t--q@1"),
    }


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
    # ``u`` is a statement nothing joins, on no way to close the root (F30-T16: neither connected
    # nor speculative, so it is the one thing the toggle adds); the dead route t@3 is drawn.
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
    """``two_routes`` plus a statement nothing joins (F30-T16: a related variant now lives in the
    column of speculative statements, so the off-route one is authored, with no pointer): on no
    way to close the root, so it is in ``all`` and not in ``routes`` and the view-toggle is
    rendered (R4)."""
    root = two_routes(tmp_path)
    proposal = scaffold.Proposal(
        node_id=VARIANT,
        target_id=TARGET,
        statement="theorem OpnProp.variant_related : ∀ p : Prop, p → p := by\n  sorry\n",
        witness="theorem witness : True := trivial\n",
        author="proposer",
        origin="authored",
        date="2026-10-01T00:00:00Z",
    )
    scaffold.validate(proposal)
    scaffold.write(fixture.nodes_dir(root), proposal)
    # A variant has no dependents, so the root is declared (F08-Q19).
    status = root / "targets" / TARGET / "status"
    status.mkdir(exist_ok=True)
    (status / "2026-10-01-curator.yaml").write_text(
        yaml.safe_dump(samples.target_status(root=ROOT_NODE)), encoding="utf-8"
    )
    return root


def followed_tree(tmp_path: Path) -> Path:
    """``two_routes`` with its second route's hole proved by a proof whose term rests on the
    root's proved dependency ``and-reassoc``: followed, that set adds ``and-reassoc``."""
    root = two_routes(tmp_path)
    gate_attest(root, DEP, n=11, footprint={"nodes": []})
    hole = nodes_dir(root) / THIRD
    statement = (hole / "Statement.lean").read_text(encoding="utf-8")
    (hole / "Proof.lean").write_text(statement.replace("sorry", "exact trivial"), encoding="utf-8")
    gate_attest(root, THIRD, n=12, footprint={"nodes": [DEP]})
    return root


DEP = "and-reassoc"

#: The selector's node positions, keyed; the toggle must not move the tree (R13).
SELECTOR_AT = """() => {
  const out = {};
  document.querySelectorAll('svg.selector g.sel-node').forEach(g => {
    out[g.getAttribute('data-key')] = g.getAttribute('transform');
  });
  return out;
}"""

#: The visible table rows' cells as read (the first line of each cell: the count shown).
ROW_TEXT = """() => [...document.querySelectorAll('tr.set-row')].filter(r => !r.hidden)
  .map(r => [...r.cells].map(c => c.innerText.trim().split('\\n')[0]))"""

#: Every node's box, translate, display and lit state; every line's ``d`` and state; the svg's
#: view and size; the open panel; the pressed selector elements; the table's shown rows.
SNAPSHOT = """() => {
  const svg = document.querySelector('svg.dag');
  const vis = el => getComputedStyle(el).display !== 'none';
  const origin = svg.getBoundingClientRect();  // boxes relative to the drawing: a hover may scroll
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
    group: (t => t ? {y: parseFloat(t.getAttribute('y')), shown: vis(t)} : null)(
      svg.querySelector('text.dag-group')),
  };
  svg.querySelectorAll('[data-node]').forEach(g => {
    const r = g.getBoundingClientRect();
    const m = /translate\\(([-\\d.]+),([-\\d.]+)\\)/.exec(g.getAttribute('transform') || '');
    out.nodes[g.getAttribute('data-node')] = {
      box: [r.x - origin.x, r.y - origin.y, r.width, r.height],
      at: m ? [parseFloat(m[1]), parseFloat(m[2])] : null,
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


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


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
    # The owner (2026-10-18): a hover reaches through the route junctions, so the root's hover
    # lights its two junctions, the lines beyond them and the three holes they lead to.
    lines = [(s, d) for s, d, _k, _p in lays["routes"]["lines"]]
    touching = {(s, d) for s, d in lines if ROOT_NODE in (s, d)}
    junctions = {x for s, d in touching for x in (s, d) if "@" in x}
    beyond = {(s, d) for s, d in lines if s in junctions or d in junctions}
    assert junctions == {f"{ROOT_NODE}@1", f"{ROOT_NODE}@2"}
    assert lit_edges(hovered) == {f"{s}>{d}" for s, d in touching | beyond}
    assert lit_nodes(hovered) == {x for s, d in touching | beyond for x in (s, d)}
    assert {*HOLE_IDS, THIRD} <= lit_nodes(hovered)  # the holes beyond the junctions
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
    # The variants' divider and label, when the markup carries them (T2 draws them only when the
    # opening layout has a loose group), follow each layout's group_y and are not drawn without one.
    if on_all["group"] is not None:
        assert on_all["group"]["shown"] == isinstance(lays["all"]["group_y"], (int, float))
        if on_all["group"]["shown"]:
            assert on_all["group"]["y"] == pytest.approx(lays["all"]["group_y"])
        assert back["group"]["shown"] == isinstance(lays["routes"]["group_y"], (int, float))
    assert "view=all" in on_all["hash"]
    assert all_label != label
    assert back["view"] == "routes" and back["toggle"] == "false"
    assert_at_layout(back, lays["routes"])
    assert on_leaf["toggle"] == "false" and on_leaf["pressed"]
    assert from_leaf["view"] == "all" and from_leaf["pressed"] == []
    assert from_leaf["toggle"] == "true"


def test_unticking_stop_at_proved_shows_the_followed_set(tmp_path: Path) -> None:
    """F27-AC14 (R13): the toggle is ticked on load; with a set selected, unticking it moves the
    drawing to the set's ``follow/`` twin (the proved dependency the hole's proof rests on
    appears, at the twin's coordinates), the selector's plain node stays pressed and nothing in
    the selector moves, the table row stays and its counts change, the hash carries the twin;
    ticking again returns to the set."""
    with browser(followed_tree(tmp_path / "g"), tmp_path / "site") as pg:
        lays = layouts_in(pg)
        key = next(k for k, lay in lays.items() if k.startswith("sel/") and THIRD in lay["nodes"])
        twin = one_view.FOLLOW + key
        box = pg.locator("input.follow-proved")
        assert box.is_visible() and box.is_checked()
        pg.locator(f'svg.selector [data-view="{key}"]').click()
        pg.mouse.move(5, 5)
        at_stop = pg.evaluate(SNAPSHOT)
        sel_stop = pg.evaluate(SELECTOR_AT)
        rows_stop = pg.evaluate(ROW_TEXT)
        box.uncheck()
        pg.mouse.move(5, 5)
        at_follow = pg.evaluate(SNAPSHOT)
        sel_follow = pg.evaluate(SELECTOR_AT)
        rows_follow = pg.evaluate(ROW_TEXT)
        box.check()
        pg.mouse.move(5, 5)
        back = pg.evaluate(SNAPSHOT)
    assert DEP in lays[twin]["nodes"] and DEP not in lays[key]["nodes"]
    assert at_stop["view"] == key and DEP not in shown_nodes(at_stop)
    assert at_follow["view"] == twin and DEP in shown_nodes(at_follow)
    assert_at_layout(at_follow, lays[twin])
    assert at_follow["pressed"] == [key] and at_follow["rows"] == [key]
    assert sel_follow == sel_stop
    assert "view=follow" in at_follow["hash"]
    # Statements and Proved each grew by one (and-reassoc); Open did not.
    (stop_row,), (follow_row,) = rows_stop, rows_follow
    assert (int(follow_row[1]), int(follow_row[2])) == (int(stop_row[1]) + 1, int(stop_row[2]) + 1)
    assert follow_row[3] == stop_row[3]
    assert back["view"] == key and DEP not in shown_nodes(back)
    assert_at_layout(back, lays[key])


def test_hovering_a_selector_node_lights_its_parent_and_children_in_the_selector(
    tmp_path: Path,
) -> None:
    """T8 (the owner, 2026-10-18): the selector has the drawing's own hover — the hovered node,
    its lines and the nodes they join are lit and the rest of the selector dimmed — beside the
    preview it already casts on the drawing; its words show in a tooltip; leaving clears both."""
    with browser(two_routes(tmp_path / "g"), tmp_path / "site") as pg:
        top = pg.locator('svg.selector g.sel-node[data-view="sel"]')
        top.hover()
        state = pg.evaluate(
            """() => {
              const s = document.querySelector('svg.selector');
              const view = el => el.getAttribute('data-view');
              const lit = [...s.querySelectorAll('.sel-node.lit')].map(view);
              const litEdges = [...s.querySelectorAll('.sel-edge.lit')].map(view);
              const faint = g => parseFloat(getComputedStyle(g).opacity) < 0.9;
              const dim = [...s.querySelectorAll('.sel-node')].filter(faint).length;
              const tip = document.querySelector('.sel-tip');
              return {lit, litEdges, dim, hovering: s.classList.contains('hovering'),
                      tip: tip && !tip.hidden ? tip.textContent : null,
                      picking: document.querySelector('svg.dag').classList.contains('picking')};
            }"""
        )
        pg.mouse.move(5, 5)
        after = pg.evaluate(
            "() => [document.querySelectorAll('svg.selector .lit').length,"
            " document.querySelector('svg.selector').classList.contains('hovering'),"
            " (t => t ? t.hidden : true)(document.querySelector('.sel-tip'))]"
        )
        # T9 (the owner): the neighbour lighting is for nodes only; an edge hover keeps the
        # drawing's preview and its own stroke, lights nothing else and shows no tooltip.
        pg.locator("svg.selector path.sel-edge[data-view]").nth(0).hover()
        on_edge = pg.evaluate(
            "() => [document.querySelectorAll('svg.selector .lit').length,"
            " document.querySelector('svg.selector').classList.contains('hovering'),"
            " (t => t ? t.hidden : true)(document.querySelector('.sel-tip')),"
            " document.querySelector('svg.dag').classList.contains('picking')]"
        )
        on_edge, edge_picking = on_edge[:3], on_edge[3]
        pg.mouse.move(5, 5)
    assert edge_picking
    leaves = {"sel/" + k for k in ("and-swap-reassoc@1", "and-swap-reassoc@2")}
    assert set(state["lit"]) == {"sel", *leaves}
    assert on_edge == [0, False, True], "an edge hover previews the drawing but lights no neighbour"
    assert set(state["litEdges"]) == {"edge/" + k for k in leaves}
    assert state["hovering"] and state["dim"] == 0  # every node of this small tree is a neighbour
    assert state["picking"], "the preview on the drawing still runs"
    assert state["tip"] and "set" in state["tip"].lower()
    assert after == [0, False, True]


# -- F31-T10 (R7; AC7): shelved statements leave the routes view and stay under the toggle -------

PAGE = f"problems/{TARGET}/index.html"
ROUTE_ONE = f"{ROOT_NODE}@1"
ROUTE_TWO = f"{ROOT_NODE}@2"


def svg_of(page: str) -> str:
    start = page.index('<svg class="dag"')
    return page[start : page.index("</svg>", start)]


def element(svg: str, node_id: str) -> str:
    """A statement's or a junction's ``g`` (a junction's ``data-route`` precedes its
    ``data-node``)."""
    pattern = rf'<g class="[^"]*"[^>]* data-node="{re.escape(node_id)}"[^>]*>.*?</g>'
    m = re.search(pattern, svg, re.S)
    assert m is not None, node_id
    return m.group(0)


def classes(svg: str, node_id: str) -> set[str]:
    m = re.search(rf'<g class="([^"]*)"[^>]* data-node="{re.escape(node_id)}"', svg)
    assert m is not None, node_id
    return set(m.group(1).split())


def page_layouts(page: str) -> dict[str, Any]:
    m = re.search(r'<script type="application/json" id="graph-layouts">(.*?)</script>', page, re.S)
    assert m is not None
    parsed: dict[str, Any] = json.loads(m.group(1))
    return parsed


def toggle_of(page: str) -> str:
    m = re.search(r'<button type="button" class="chip view-toggle"[^>]*>[^<]*</button>', page)
    assert m is not None, "no view-toggle"
    return m.group(0)


def render_shelved(root: Path, shelved: dict[str, dict[str, Any]]) -> dict[str, str]:
    """The tree's products as the gate renders them, then shelved as the v3.47 gate would
    leave them (the derivation is not on this branch), then the site."""
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    fixture.publish_shelved(root, shelved)
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def test_a_shelved_hole_is_under_the_toggle_not_on_the_routes_view(tmp_path: Path) -> None:
    """R7, Q2: a shelved statement is in ``all`` and not in ``routes``; its pill carries
    ``shelved`` and the cause on hover; the toggle counts it apart from the off-route ones; the
    route it sits on keeps its junction while a sibling hole is live. The Problems row reads
    shelved and offers no work."""
    root = two_routes(tmp_path)
    pages = render_shelved(
        root,
        {HOLE_IDS[0]: fixture.shelved_fact("Too <b>weak</b> to help the root", via=HOLE_IDS[0])},
    )
    page = pages[PAGE]
    lays = page_layouts(page)
    assert HOLE_IDS[0] in lays["all"]["nodes"] and HOLE_IDS[0] not in lays["routes"]["nodes"]
    assert HOLE_IDS[1] in lays["routes"]["nodes"] and ROUTE_ONE in lays["routes"]["nodes"]
    svg = svg_of(page)
    cls = classes(svg, HOLE_IDS[0])
    assert {"shelved", "off-view"} <= cls, cls
    assert "shelved" not in classes(svg, HOLE_IDS[1])
    title = re.search(r"<title>(.*?)</title>", element(svg, HOLE_IDS[0])).group(1)  # type: ignore[union-attr]
    assert "shelved by alice on 2026-10-24: Too &lt;b&gt;weak&lt;/b&gt; to help the root" in title
    assert "<b>" not in title
    toggle = toggle_of(page)
    assert "Show 1 more statement" in toggle and "1 shelved" in toggle, toggle
    rows_ = re.findall(r'<div class="stmt".*?</div>', pages["problems/index.html"], re.S)
    stmt = next(r for r in rows_ if f"/{HOLE_IDS[0]}/" in r)
    assert 'data-state="shelved"' in stmt and 'data-workable="0"' in stmt
    assert "Supply a witness" not in stmt and "Work on this" not in stmt


def test_a_route_whose_holes_are_all_shelved_loses_its_junction(tmp_path: Path) -> None:
    """R7: a retired route (every hole shelved through the parent's route record) draws no
    junction in ``routes``; the junction stays in ``all``, dead, and says why; the toggle counts
    the two statements and not the junction; the sibling route is untouched."""
    root = two_routes(tmp_path)
    retired = {
        h: fixture.shelved_fact("Route 1 is a distraction", via=ROOT_NODE, scope="route")
        for h in HOLE_IDS
    }
    page = render_shelved(root, retired)[PAGE]
    lays = page_layouts(page)
    assert ROUTE_ONE not in lays["routes"]["nodes"] and ROUTE_ONE in lays["all"]["nodes"]
    assert ROUTE_TWO in lays["routes"]["nodes"] and THIRD in lays["routes"]["nodes"]
    svg = svg_of(page)
    junction = element(svg, ROUTE_ONE)
    assert {"junction", "dead", "off-view"} <= classes(svg, ROUTE_ONE)
    assert "retired" in junction and "Route 1 is a distraction" in junction
    assert "Show 2 more statements" in toggle_of(page) and "2 shelved" in toggle_of(page)


def shelved_doc() -> dict[str, Any]:
    """Root ``t`` with two routes, ``[a, b]`` (``b`` proved and shelved) and ``[c]`` (``c``
    open and shelved)."""
    rows = [
        node("t", origin="authored", routes=[["t--a", "t--b"], ["t--c"]]),
        node("t--a"),
        node("t--b", "proved"),
        node("t--c"),
    ]
    for row in rows:
        row["shelved"] = (
            fixture.shelved_fact(via=str(row["node_id"]))
            if row["node_id"] in ("t--b", "t--c")
            else None
        )
    return {"schema": "graph/v15", "target_id": "t", "root": "t", "nodes": rows}


def test_a_shelved_member_stays_in_a_set_view_only_when_proved() -> None:
    """Q6: a shelved proved statement keeps its place in a set (drawn dim); a shelved open one
    leaves every set view; neither is in ``routes``; both are in ``all`` (Q2: the order seed)."""
    g = shelved_doc()
    vs = one_view.views(g, routes.read(g, []))
    assert {"t--b", "t--c"} <= set(vs[one_view.ALL].nodes)
    assert not {"t--b", "t--c"} & set(vs[one_view.ROUTES].nodes)
    set_views = [v for k, v in vs.items() if k == one_view.TOP or k.startswith(("sel/", "edge/"))]
    assert set_views
    assert any("t--b" in v.nodes for v in set_views)
    assert all("t--c" not in v.nodes for v in set_views)
    assert all("t--c" not in (ln[0], ln[1]) for v in set_views for ln in v.lines), (
        "a line to a dropped statement"
    )
    d = one_view.drawing(g, [], href={})
    svg = d.svg
    assert {"shelved", "proved"} <= classes(svg, "t--b")
    assert "shelved" in classes(svg, "t--c") and "shelved" not in classes(svg, "t--a")
    assert "shelved" in d.marks
    assert d.shelved == 2 and d.hidden == 2
