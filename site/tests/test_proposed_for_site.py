"""F18-T6 (R8, R9), restated by F30-T11 (D-14 v3.26 as amended by v3.46): a crux's pointer to
the node it was proposed for, in the product and on the page.

The six crux statements on erdos-1050 said in their doc comments which hole they were written for
and nowhere a machine could read it; the page drew them as six unconnected proved pills. A
``proposed-for`` record (D-14 v3.26) names the node; ``graph.json`` publishes the latest as
``proposed_for``. F18 drew it as a dashed line; the owner's reading of erdos-257 (2026-10-21) was
that a line from a proved spec to an unproved root meant nothing, so the crux is now drawn in the
band of proposed statements under the tree, its pointer words on the pill, and the only lines
from it are the ones the record measured (a use), lit on hover. A crux a statement declares as
a dependency stays in the tree, where its solid line already says more.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import fixture
import yaml
from harness import TARGET, copy_graph
from test_crux_band import CRUX, band_tree
from test_products import ROOT_NODE

from opn_gate import products
from opn_site import dag, model, render

REPO = "https://github.com/example/graph"
DEP_CRUX, FOR = "tutorial-and-swap", "and-reassoc"


def point(root: Path, crux: str = DEP_CRUX, node: str = FOR) -> None:
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


def band_of(page: str) -> str:
    m = re.search(r'<svg class="dag band".*?</svg>', page, re.S)
    assert m is not None, "no band"
    return m.group(0)


def test_the_pointer_is_published_and_the_crux_is_drawn_in_the_band(tmp_path: Path) -> None:
    rows, page = rendered(band_tree(tmp_path))
    assert rows[CRUX]["proposed_for"] == ROOT_NODE
    assert all(r["proposed_for"] is None for nid, r in rows.items() if nid != CRUX)
    band = band_of(page)
    assert f'data-node="{CRUX}"' in band
    main = page[: page.index('<svg class="dag band"')]
    assert f'data-node="{CRUX}"' not in main.split('<svg class="dag"', 1)[1]
    assert "edge proposed" not in page
    assert re.search(rf'<path class="band-link edge use" data-from="{CRUX}" data-to="', page)
    key = re.search(r'<div class="dag-legend">(.*?)</div>', page, re.S)
    assert key is not None and "proposed statement" in key.group(1)
    assert f"proposed for: {ROOT_NODE}" in band or "proposed for: " in band


def test_no_pointer_no_band_and_no_key_entry(tmp_path: Path) -> None:
    _rows, page = rendered(copy_graph(tmp_path, publish=True))
    assert "edge proposed" not in page and 'class="dag band"' not in page
    key = re.search(r'<div class="dag-legend">(.*?)</div>', page, re.S)
    assert key is not None and "proposed statement" not in key.group(1)


def test_a_crux_declared_as_a_dependency_stays_in_the_tree(tmp_path: Path) -> None:
    """``tutorial-and-swap`` is a dependency of the root: pointing it at ``and-reassoc`` draws
    no band and no line, and the pill keeps its solid dependency line into the root."""
    root = copy_graph(tmp_path, publish=True)
    point(root)
    rows, page = rendered(root)
    assert rows[DEP_CRUX]["proposed_for"] == FOR
    assert 'class="dag band"' not in page and "edge proposed" not in page
    assert re.search(rf'<path class="edge[^"]*" data-from="{DEP_CRUX}" data-to="{ROOT_NODE}"', page)


def test_a_used_crux_stays_in_the_band_and_the_use_is_its_lit_line() -> None:
    """Once a merged proof uses the crux the use is the band's line into the tree; nothing
    moves the crux into the tree."""
    nodes: list[dict[str, Any]] = [
        {"node_id": "n", "status": "proved", "deps": [], "uses": ["c"], "proposed_for": None},
        {"node_id": "c", "status": "proved", "deps": [], "uses": [], "proposed_for": "n"},
    ]
    lay = dag.layout(nodes, root="n")
    assert lay.band == ("c",) and [(e.src, e.dst, e.kind) for e in lay.links] == [
        ("c", "n", "edge use")
    ]
    svg = dag.svg(nodes, href={"n": "/n", "c": "/c"})
    assert 'class="edge use band-link" data-from="c" data-to="n"' in svg
    assert "edge proposed" not in svg


def test_the_crux_is_drawn_beneath_the_tree_not_under_the_node_it_serves() -> None:
    nodes: list[dict[str, Any]] = [
        {"node_id": "n", "status": "ready", "deps": [], "uses": [], "proposed_for": None},
        {"node_id": "c", "status": "proved", "deps": [], "uses": [], "proposed_for": "n"},
    ]
    assert dag.layers(nodes) == {"c": 0, "n": 0}
    lay = dag.layout(nodes, root="n")
    at = {p.node_id: p for p in lay.placed}
    assert at["c"].y > at["n"].y + dag.NODE_H and lay.band == ("c",)
