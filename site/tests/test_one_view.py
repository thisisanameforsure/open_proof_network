"""F30: one statement graph (the owner's request of 2026-10-18).

T1 (R6, R10; AC2, AC3, AC4): the views and their layouts. A view is a subset of the merged
graph (statements and route junctions) with the lines between them: ``all``, ``routes``, one per
selector node (the union of the sets beneath it), one per selector edge (the committed segment),
one per proof. Every view is laid out by ``dag.layout`` seeded with the full layout's order, so
statements shared by two views keep their left-to-right order.
"""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any

import pytest
from test_finding_dag_layout import crossings
from test_routes_view import doc, nested_doc, node
from test_target_routes import live

from opn_gate import routes
from opn_site import dag, one_view

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
