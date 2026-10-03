"""F18-T6 (R8, R9): a crux's pointer to the node it was proposed for, in the product and drawn.

The six crux statements on erdos-1050 said in their doc comments which hole they were written for
and nowhere a machine could read it; the page drew them as six unconnected proved pills. A
``proposed-for`` record (D-14 v3.26) names the node; ``graph.json`` publishes the latest as
``proposed_for``; the page draws it as a dashed line until a merged proof uses the crux, when the
use line (F08-R19) says more and replaces it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import fixture
import yaml
from harness import TARGET, copy_graph

from opn_gate import products
from opn_site import dag, model, render

REPO = "https://github.com/example/graph"
CRUX, FOR = "tutorial-and-swap", "and-reassoc"


def point(root: Path, crux: str = CRUX, node: str = FOR) -> None:
    d = root / "targets" / TARGET / "nodes" / crux / "proposed-for"
    d.mkdir(exist_ok=True)
    doc = {"schema": "proposed-for/v1", "for": node, "author": "alice", "date": "2026-10-03"}
    (d / "20261003T120000Z-alice.yaml").write_text(yaml.safe_dump(doc), encoding="utf-8")


def rendered(root: Path) -> tuple[dict[str, dict[str, object]], str]:
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    rows = {
        str(n["node_id"]): n
        for n in json.loads((root / "targets" / TARGET / "graph.json").read_text())["nodes"]
    }
    site = model.load_site(root, fixture.COMMIT)
    return rows, render.render_site(site, repo_url=REPO)[f"problems/{TARGET}/index.html"]


def test_the_pointer_is_published_and_drawn_dashed(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    point(root)
    rows, page = rendered(root)
    assert rows[CRUX]["proposed_for"] == FOR
    assert all(r["proposed_for"] is None for nid, r in rows.items() if nid != CRUX)
    assert re.search(
        rf'<line class="edge proposed[^"]*" data-from="{CRUX}" data-to="{FOR}"', page
    ), "no dashed proposed-for line"
    key = re.search(r'<div class="dag-legend">(.*?)</div>', page, re.S)
    assert key is not None and "proposed for" in key.group(1)


def test_no_pointer_no_line_and_no_key_entry(tmp_path: Path) -> None:
    _rows, page = rendered(copy_graph(tmp_path, publish=True))
    assert "edge proposed" not in page
    key = re.search(r'<div class="dag-legend">(.*?)</div>', page, re.S)
    assert key is not None and "proposed for" not in key.group(1)


def test_a_use_replaces_the_pointer() -> None:
    """Once a merged proof uses the crux the use line is drawn and the dashed one is not."""
    nodes: list[dict[str, Any]] = [
        {"node_id": "n", "status": "proved", "deps": [], "uses": ["c"], "proposed_for": None},
        {"node_id": "c", "status": "proved", "deps": [], "uses": [], "proposed_for": "n"},
    ]
    svg = dag.svg(nodes, href={"n": "/n", "c": "/c"})
    assert 'class="edge use" data-from="c" data-to="n"' in svg
    assert "edge proposed" not in svg


def test_the_crux_is_drawn_beneath_the_node_it_serves() -> None:
    nodes: list[dict[str, Any]] = [
        {"node_id": "n", "status": "ready", "deps": [], "uses": [], "proposed_for": None},
        {"node_id": "c", "status": "proved", "deps": [], "uses": [], "proposed_for": "n"},
    ]
    assert dag.layers(nodes) == {"c": 0, "n": 1}
