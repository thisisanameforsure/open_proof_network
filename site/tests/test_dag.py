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
