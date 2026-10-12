"""F04-T39 (D-12 v3.38): a lemma — a node under another branch that a merged partial of this
node restated as a hole — is drawn, keyed, listed and lit.

The finding (2026-10-09b, C1, erdos-1094): a partial on ``--h3`` restated ``--h2--h1--h1`` and
the gate added no edge, so the merged assembly could never be used. Decisions v3.38 give the
parent the node as a *lemma* (``graph/v8`` ``lemmas: [{hole, node}]``) with a hole's standing:
drawn on once proved, never waited on. On the site that is one more kind of line (``edge
lemma``, dash-dot, from the lemma up to the parent), a key entry whenever the drawing has one, a
list on the node page beside the dependencies, a decomposition hole resolving to the lemma's
node, and the lemma's line lit when either end is hovered.
"""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from typing import Any

import fixture
import pytest
from test_finding_dag_layout import SHAPES, behind_pills, crossings, drawn

from opn_gate import schemas
from opn_site import dag, model, render

REPO = "https://github.com/example/graph"
TARGET = "propositional"
ROOT = "and-swap-reassoc"
PARENT = fixture.LEMMA_PARENT
LEMMA = fixture.LEMMA_NODE
HOLE = fixture.LEMMA_HOLE
STATIC = Path(render.__file__).resolve().parent / "static"
CSS = (STATIC / "site.css").read_text(encoding="utf-8")
KEY_WORD = "lemma from another branch"

#: The live erdos-1094 shape after v3.38: ``--h3`` points at ``--h2--h1--h1`` under ``--h2--h1``
#: under ``--h2`` — the lemma's line crosses from one branch to another.
LIVE_1094 = "erdos-1094"


def shape_nodes() -> list[dict[str, Any]]:
    """Three statements with one lemma, as ``graph/v8`` rows: ``b`` rests on ``a`` as a lemma
    and declares nothing."""
    return [
        {"node_id": "r", "status": "ready", "deps": ["a", "b"], "lemmas": []},
        {"node_id": "a", "status": "proved", "deps": [], "lemmas": []},
        {"node_id": "b", "status": "ready", "deps": [], "lemmas": [{"hole": "h_a", "node": "a"}]},
    ]


# --- 1. the model reads graph/v8 ----------------------------------------------------------------


def test_the_site_accepts_graph_v7_and_every_older_version() -> None:
    accepted = model.PRODUCT_SCHEMAS["graph.json"]
    assert "graph/v8" in accepted
    assert all(f"graph/v{n}" in accepted for n in range(1, 7))


def test_a_node_reads_its_lemmas_and_an_older_row_reads_none(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    tv = site.targets[TARGET]
    assert tv.graph["schema"] == "graph/v8"
    assert tv.nodes[PARENT].lemmas == [model.LemmaRef(hole=HOLE, node=LEMMA)]
    assert tv.nodes[ROOT].lemmas == []
    older = dataclasses.replace(
        tv.nodes[PARENT],
        graph_entry={k: v for k, v in tv.nodes[PARENT].graph_entry.items() if k != "lemmas"},
    )
    assert older.lemmas == []


def test_the_fixture_graph_validates_as_graph_v7(tmp_path: Path) -> None:
    root = fixture.build(tmp_path)
    graph = json.loads((root / "targets" / TARGET / "graph.json").read_text(encoding="utf-8"))
    schemas.validate(graph, "graph/v8")
    row = next(n for n in graph["nodes"] if n["node_id"] == PARENT)
    assert row["lemmas"] == [{"hole": HOLE, "node": LEMMA}]
    assert LEMMA not in row["deps"], "a lemma is not a declared dependency (D-3)"


# --- 2. the drawing ------------------------------------------------------------------------------


def test_a_lemma_is_below_its_parent() -> None:
    """Layering treats a lemma as something the parent rests on, like a hole child."""
    nodes = shape_nodes()
    assert dag.below(nodes[2]) == ["a"]
    assert dag.layers(nodes) == {"a": 0, "b": 1, "r": 2}


def test_a_lemma_line_has_its_own_kind() -> None:
    assert ("a", "b", "edge lemma") in dag.lines(shape_nodes())


def test_a_lemma_that_is_also_a_dep_or_a_use_keeps_the_stronger_line() -> None:
    nodes = shape_nodes()
    nodes[2]["deps"] = ["a"]
    kinds = {(s, d): k for s, d, k in dag.lines(nodes)}
    assert kinds[("a", "b")] == "edge"
    nodes[2]["deps"] = []
    nodes[2]["uses"] = ["a"]
    kinds = {(s, d): k for s, d, k in dag.lines(nodes)}
    assert kinds[("a", "b")] == "edge use"


def test_a_lemma_outside_the_graph_draws_no_line() -> None:
    nodes = shape_nodes()
    nodes[2]["lemmas"] = [{"hole": "h", "node": "phantom"}]
    assert all(s != "phantom" for s, _d, _k in dag.lines(nodes))
    assert dag.layers(nodes)["b"] == 0


def test_the_svg_draws_the_lemma_line_with_its_class() -> None:
    nodes = shape_nodes()
    out = dag.svg(nodes, href={n["node_id"]: "/x/" for n in nodes}, root="r")
    assert re.search(r'<path class="edge lemma[^"]*" data-from="a" data-to="b"', out)


def test_the_live_erdos_1094_shape_is_in_the_fixture_and_draws_its_lemma() -> None:
    shape = SHAPES[LIVE_1094]
    h3 = next(n for n in shape["nodes"] if n["node_id"] == f"{LIVE_1094}--h3")
    assert h3["lemmas"] == [{"hole": "h_good_below_cube", "node": f"{LIVE_1094}--h2--h1--h1"}]
    lay = drawn(LIVE_1094)
    lemma = [e for e in lay.edges if e.kind == "edge lemma"]
    assert [(e.src, e.dst) for e in lemma] == [(f"{LIVE_1094}--h2--h1--h1", f"{LIVE_1094}--h3")]


def test_the_lemma_crossing_branches_still_draws_with_no_crossing() -> None:
    lay = drawn(LIVE_1094)
    assert crossings(lay) == []
    assert behind_pills(lay) == []


def test_the_stylesheet_gives_the_lemma_line_a_stroke_of_its_own() -> None:
    """Distinguishable from the solid dep, the dashed use and the dotted pointer, in both themes:
    the rule sets a dasharray that neither of those uses, and the key's swatch matches it."""
    rule = re.search(r"^\.dag \.edge\.lemma \{([^}]*)\}", CSS, re.M)
    assert rule is not None
    dashes = re.search(r"stroke-dasharray:\s*([^;]+);", rule.group(1))
    assert dashes is not None
    for other in (r"\.dag \.edge\.use", r"\.dag \.edge\.proposed"):
        o = re.search(rf"^{other} \{{([^}}]*)\}}", CSS, re.M)
        assert o is not None
        od = re.search(r"stroke-dasharray:\s*([^;]+);", o.group(1))
        assert od is None or od.group(1).split() != dashes.group(1).split()
    assert ".dot-lemma" in CSS


# --- 3. the key ----------------------------------------------------------------------------------


def legend(html: str) -> str:
    m = re.search(r'<div class="dag-legend">(.*?)</div>', html, re.S)
    assert m is not None, "the problem page has no graph key"
    return m.group(1)


def page(tmp_path: Path) -> tuple[Any, Any, str]:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    tv = site.targets[TARGET]
    r = render.Renderer(site, repo_url=REPO, decisions_doc=None)
    return site, tv, r.target(tv)


def test_the_key_names_the_lemma_line_when_the_drawing_has_one(tmp_path: Path) -> None:
    _site, tv, html = page(tmp_path)
    assert "lemma" in render.Renderer.proof_legend(tv)
    assert f'<span class="dot dot-lemma"></span>{KEY_WORD}<span class="term-card"' in legend(html)


def test_the_key_omits_the_lemma_line_when_no_statement_has_one(tmp_path: Path) -> None:
    _site, tv, _html = page(tmp_path)
    rows = [{**n, "lemmas": []} for n in tv.graph["nodes"]]
    bare = dataclasses.replace(tv, graph={**tv.graph, "nodes": rows})
    assert "lemma" not in render.Renderer.proof_legend(bare)


def test_the_glossary_defines_the_lemma_line() -> None:
    word, meaning, proto = render.GLOSSARY_BY_KEY["lemma"]
    assert word == KEY_WORD
    assert "once it is proved" in meaning and "never waits" in meaning
    assert "D-12 v3.38" in proto


# --- 4. the node page ----------------------------------------------------------------------------


def node_page(tmp_path: Path, node_id: str) -> str:
    root = fixture.build(tmp_path)
    site = model.load_site(root, fixture.COMMIT)
    r = render.Renderer(site, repo_url=REPO, decisions_doc=None)
    return r.node(site.targets[TARGET].nodes[node_id])


def test_the_node_page_lists_the_lemmas_it_may_use(tmp_path: Path) -> None:
    html = node_page(tmp_path, PARENT)
    block = re.search(r'<div class="lemmas">(.*?)</div>', html, re.S)
    assert block is not None, "no lemma list on the parent's page"
    assert "Lemmas it may use" in block.group(1)
    assert f"/nodes/{TARGET}/{LEMMA}/" in block.group(1)
    assert f"<code>{HOLE}</code>" in block.group(1)
    assert '<span class="dot dot-proved"></span>' in block.group(1)  # the lemma's status pill
    # The list sits beside the dependencies, inside the statement block.
    assert html.index('<div class="lemmas">') > html.index('class="deps"')
    assert html.index('<div class="lemmas">') < html.index("<h2>Proof</h2>")


def test_a_node_with_no_lemma_lists_none(tmp_path: Path) -> None:
    html = node_page(tmp_path, ROOT)
    assert '<div class="lemmas">' not in html
    assert "Lemmas it may use" not in html


# --- 5. a decomposition's hole resolves to the lemma's node ----------------------------------


def test_a_hole_that_became_a_lemma_links_the_lemma_node(tmp_path: Path) -> None:
    """``graph/v8`` ``decompositions[].holes[].node`` may be the lemma's node; the outline and
    partial listings link it like any node the tree holds, with its state."""
    _site, tv, _html = page(tmp_path)
    r = render.Renderer(_site, repo_url=REPO, decisions_doc=None)
    link = r.hole_link(tv, {"name": HOLE, "node": LEMMA})
    assert f"<code>{HOLE}</code> → " in link
    assert f'<a href="#node={LEMMA}">{LEMMA}</a>' in link and "proved" in link
    step = r.step_hole(tv, {"closed_by": {"kind": "hole"}, "child_node": LEMMA})
    assert f"/nodes/{TARGET}/{LEMMA}/" in step and "proved" in step


# --- 6. hover ------------------------------------------------------------------------------------


def test_hovering_lights_the_lemma_line_too() -> None:
    """The script lights every ``path.edge``; a lemma's line is one (class ``edge lemma``)."""
    js = (STATIC / "problem.js").read_text(encoding="utf-8")
    assert 'querySelectorAll("path.edge")' in js
    nodes = shape_nodes()
    out = dag.svg(nodes, href={n["node_id"]: "/x/" for n in nodes}, root="r")
    assert re.search(r'<path class="edge lemma[^"]*" data-from="a" data-to="b"', out)


# --- 7. measured in a browser (the evidence run) ------------------------------------------------


SHOOT = Path(__file__).resolve().parents[2] / "engineering/evidence/F04/task-39-shoot.py"


def test_measured_in_a_browser(tmp_path: Path) -> None:
    """The 2026-09-19 rule, as a test: every key label sits inside the key, every pill label
    inside its pill (getBBox), no sideways scroll at 390 (scrollWidth), and the lemma's line is
    lit when the parent is hovered. The evidence script beside the screenshots does the
    measuring, so the shots and the assertions come from one run. Needs Playwright's Chromium
    (``uv run --frozen --with playwright pytest site/tests/test_finding_lemma_edge.py``); without
    it the test skips, which proves nothing."""
    pytest.importorskip("playwright.sync_api")
    import importlib.util  # noqa: PLC0415

    spec = importlib.util.spec_from_file_location("task_39_shoot", SHOOT)
    assert spec is not None and spec.loader is not None
    shoot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shoot)

    root = fixture.build(tmp_path / "graph")
    out = tmp_path / "site"
    site = model.load_site(root, fixture.COMMIT)
    render.write(render.render_site(site, repo_url=REPO), out)
    report = shoot.measure(out, tmp_path / "shots", target=TARGET, parent=PARENT, lemma=LEMMA)
    for width in (1440, 390):
        assert report[f"problem@{width}"]["scrollWidth"] <= width, report
        assert report[f"node@{width}"]["scrollWidth"] <= width, report
        assert report[f"problem@{width}"]["key_overflow"] == [], report
        assert report[f"problem@{width}"]["pill_overflow"] == [], report
        assert KEY_WORD in report[f"problem@{width}"]["key_words"], report
    assert report["hover"]["lit_lemma"] == [[LEMMA, PARENT]], report
    assert report["hover"]["lit_pills"] == sorted([LEMMA, PARENT, ROOT]), report
