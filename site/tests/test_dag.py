"""F04-T1: the DAG SVG (R6; AC10)."""

from __future__ import annotations

import re
from typing import Any

import pytest

from opn_site import dag

NODES: list[dict[str, Any]] = [
    {"node_id": "and-reassoc", "status": "proved", "deps": []},
    {
        "node_id": "and-swap-reassoc",
        "status": "ready",
        "deps": ["tutorial-and-swap", "and-reassoc"],
    },
    {"node_id": "tutorial-and-swap", "status": "proved", "deps": []},
]


def test_layers_are_longest_paths() -> None:
    assert dag.layers(NODES) == {"and-reassoc": 0, "and-swap-reassoc": 1, "tutorial-and-swap": 0}
    chain = [
        {"node_id": "a", "status": "ready", "deps": []},
        {"node_id": "b", "status": "ready", "deps": ["a"]},
        {"node_id": "c", "status": "ready", "deps": ["a", "b"]},
    ]
    assert dag.layers(chain) == {"a": 0, "b": 1, "c": 2}
    with pytest.raises(ValueError, match="cycle"):
        dag.layers([{"node_id": "x", "status": "ready", "deps": ["x"]}])


def test_dag_svg_structure() -> None:
    """AC10: one node element per node with its status class, one edge per dep."""
    href = {n["node_id"]: f"/nodes/t/{n['node_id']}/" for n in NODES}
    out = dag.svg(NODES, href=href)
    assert out.startswith("<svg") and out.endswith("</svg>")
    groups = re.findall(r'<g class="node status-([a-z]+)" data-node="([^"]+)"', out)
    assert sorted(groups) == [
        ("proved", "and-reassoc"),
        ("proved", "tutorial-and-swap"),
        ("ready", "and-swap-reassoc"),
    ]
    edges = re.findall(r'<line class="edge" data-from="([^"]+)" data-to="([^"]+)"', out)
    assert sorted(edges) == [
        ("and-reassoc", "and-swap-reassoc"),
        ("tutorial-and-swap", "and-swap-reassoc"),
    ]
    assert 'href="/nodes/t/and-reassoc/"' in out
    # Root on top: its y is smaller than its deps'.
    placed, _w, _h = dag.place(NODES)
    ys = {p.node_id: p.y for p in placed}
    assert ys["and-swap-reassoc"] < ys["and-reassoc"] == ys["tutorial-and-swap"]


def test_svg_escapes_ids() -> None:
    nodes = [{"node_id": "a<b", "status": "ready", "deps": []}]
    out = dag.svg(nodes, href={"a<b": "/nodes/t/a%3Cb/"})
    assert "a<b" not in out and "a&lt;b" in out


# --- edges of the layout (R6): what a malformed or hostile graph.json does to the SVG ------------


def test_empty_graph_is_a_valid_empty_svg() -> None:
    assert dag.layers([]) == {}
    out = dag.svg([], href={})
    assert out.startswith("<svg") and out.endswith("</svg>")
    assert "<g" not in out and "<line" not in out


def test_dep_on_a_node_outside_the_graph_draws_no_edge() -> None:
    """A dangling dep is not an edge to nowhere; the node is still placed (the page-level link
    check is what refuses the build, R13)."""
    nodes = [{"node_id": "a", "status": "ready", "deps": ["phantom"]}]
    assert dag.layers(nodes) == {"a": 0}
    out = dag.svg(nodes, href={"a": "/nodes/t/a/"})
    assert "<line" not in out and 'data-node="a"' in out


def test_longer_cycle_is_named_in_order() -> None:
    nodes = [
        {"node_id": "a", "status": "ready", "deps": ["c"]},
        {"node_id": "b", "status": "ready", "deps": ["a"]},
        {"node_id": "c", "status": "ready", "deps": ["b"]},
    ]
    with pytest.raises(ValueError, match=r"dependency cycle: a -> c -> b -> a"):
        dag.layers(nodes)


def test_svg_escapes_status_and_href() -> None:
    """Status lands in a class attribute and href in an attribute; both are escaped."""
    nodes = [{"node_id": "a", "status": 'x"><script>alert(1)</script>', "deps": []}]
    out = dag.svg(nodes, href={"a": '/nodes/t/a/"><script>'})
    assert "<script>" not in out
    assert 'class="node status-x&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;"' in out
    assert 'href="/nodes/t/a/&quot;&gt;&lt;script&gt;"' in out
    assert "<title>a: x&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;</title>" in out


def test_long_node_id_is_truncated_in_the_label_but_whole_in_the_title() -> None:
    """F04-T10: head, ellipsis and tail within 22 characters; the id whole in the title."""
    node_id = "b" * 23 + "a" * 9 + "c" * 8
    out = dag.svg([{"node_id": node_id, "status": "ready", "deps": []}], href={node_id: "/n/"})
    assert f">{'b' * 23}…{'c' * 8}</text>" in out
    assert f"<title>{node_id}: ready</title>" in out and f'data-node="{node_id}"' in out


def test_svg_requires_an_href_for_every_node() -> None:
    """The renderer passes a path for every node; a missing one is a programming error, not a
    silently unlinked node."""
    with pytest.raises(KeyError):
        dag.svg([{"node_id": "a", "status": "ready", "deps": []}], href={})


def test_layout_is_deterministic_regardless_of_input_order() -> None:
    reordered = list(reversed(NODES))
    assert dag.svg(NODES, href={n["node_id"]: "/x/" for n in NODES}) == dag.svg(
        reordered, href={n["node_id"]: "/x/" for n in NODES}
    )


def test_short_label_keeps_a_fitting_id_whole_and_every_long_one_at_the_limit() -> None:
    """F04-T10's label rule at its edges: LABEL_MAX characters fit; one more is cut to
    LABEL_MAX with the tail."""
    assert dag.short_label("") == ""
    assert dag.short_label("x" * dag.LABEL_MAX) == "x" * dag.LABEL_MAX
    long_id = "h" * (dag.LABEL_MAX - 8) + "t" * 9
    assert len(long_id) == dag.LABEL_MAX + 1
    label = dag.short_label(long_id)
    assert len(label) == dag.LABEL_MAX
    assert label.endswith("t" * dag.LABEL_TAIL) and label.startswith("h" * (dag.LABEL_MAX - 9))
    assert "…" in label


# --- F04-T24: a wide layer wraps -----------------------------------------------------------------


def _wide() -> list[dict[str, object]]:
    """The live euclid-primes shape (2026-09-20): a root over nine statements in one layer."""
    leaves = [f"variant-{i:08x}" for i in range(9)]
    nodes: list[dict[str, object]] = [
        {"node_id": n, "deps": [], "status": "proved"} for n in leaves
    ]
    nodes.append({"node_id": "root", "deps": leaves[:4], "status": "proved"})
    return nodes


def test_a_wide_layer_wraps_instead_of_shrinking_the_drawing() -> None:
    """The stylesheet scales a drawing down to its column, so nine pills in one row were drawn
    at a few pixels high: unreadable labels in a mostly empty box (seen on the live page). A
    layer wider than ``MAX_ROW_W`` is laid out on as many rows as it needs, at full size."""
    placed, width, height = dag.place(_wide())
    assert width <= dag.MAX_ROW_W + 2 * dag.PAD
    rows = {p.y for p in placed if p.layer == 0}
    assert len(rows) > 1, "the wide layer stayed on one row"
    assert all(p.x >= 0 and p.x + p.w <= width and p.y + dag.NODE_H <= height for p in placed)
    # no two pills overlap
    for a in placed:
        for b in placed:
            if a is not b and a.y == b.y:
                assert a.x + a.w <= b.x or b.x + b.w <= a.x, (a, b)
    # the root is still above everything it depends on
    root = next(p for p in placed if p.node_id == "root")
    assert all(root.y < p.y for p in placed if p.layer == 0)


def test_a_graph_that_fits_is_laid_out_exactly_as_before() -> None:
    nodes = [
        {"node_id": "a", "deps": [], "status": "proved"},
        {"node_id": "b", "deps": [], "status": "ready"},
        {"node_id": "r", "deps": ["a", "b"], "status": "ready"},
    ]
    placed, width, height = dag.place(nodes)
    assert {p.y for p in placed if p.layer == 0} == {dag.PAD + dag.NODE_H + dag.GAP_Y}
    assert height == dag.PAD * 2 + 2 * dag.NODE_H + dag.GAP_Y
    assert width == dag.PAD * 2 + dag.node_width("a") + dag.GAP_X + dag.node_width("b")
