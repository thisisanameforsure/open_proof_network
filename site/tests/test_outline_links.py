"""F18-T4, T5 (R5, R7; AC6): the outlines on the problem page, and how the graph follows them.

The owner, 2026-10-03: the natural-language proof outlines should be visible on the graph, with
clear tracking of how the graph is following the outline. They existed — annexes (D-31), three on
erdos-1050's root and five on h1-v2 — and were shown only on each node's own page. Now the graph
marks a node that has outlines; its panel lists each outline as followed by the skeleton that
cites it (with the holes that skeleton made) or as not followed; and a stepped outline (annex/v2,
D-31 v3.26) is a checklist of its steps against the nodes named after them. Outline text is the
contributor's and is shown as such, escaped (C9, D-28).
"""

from __future__ import annotations

import re
from pathlib import Path

import fixture
from harness import TARGET, copy_graph
from test_annex_steps import outline_annex
from test_decompositions import HOLE_IDS, add_hole, merged_partial
from test_products import ROOT_NODE, nodes_dir

from opn_gate import products
from opn_site import model, render

REPO = "https://github.com/example/graph"
CITED = "a" * 64
OTHER = "b" * 64


def page_of(root: Path) -> str:
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    site = model.load_site(root, fixture.COMMIT)
    return render.render_site(site, repo_url=REPO)[f"problems/{TARGET}/index.html"]


def two_outlines(tmp_path: Path) -> Path:
    """The root carries two outlines; a merged skeleton followed one and made one hole."""
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    merged_partial(root, 7, ["hden"], annex=CITED)
    (nodes_dir(root) / ROOT_NODE / "annex" / f"{OTHER}.md").write_text(
        "# Another route <script>alert(1)</script>\n\nUntried.\n", encoding="utf-8"
    )
    return root


def panel(page: str, node_id: str) -> str:
    m = re.search(rf'<div class="card panel" data-node="{node_id}".*?\n</div>', page, re.S)
    assert m is not None, node_id
    return m.group(0)


def test_a_node_with_outlines_is_marked_on_the_graph(tmp_path: Path) -> None:
    page = page_of(two_outlines(tmp_path))
    pill = re.search(rf'<g class="node[^"]*" data-node="{ROOT_NODE}".*?</g></a>', page, re.S)
    assert pill is not None
    assert re.search(r'<g class="outline-mark"[^>]*>.*?<text[^>]*>2</text>', pill.group(0), re.S)
    hole = re.search(rf'<g class="node[^"]*" data-node="{HOLE_IDS[0]}".*?</g></a>', page, re.S)
    assert hole is not None and "outline-mark" not in hole.group(0)


def test_the_panel_says_which_outline_was_followed_and_by_what(tmp_path: Path) -> None:
    body = panel(page_of(two_outlines(tmp_path)), ROOT_NODE)
    followed = re.search(rf'<li class="outline" data-annex="{CITED}">(.*?)</li>', body, re.S)
    assert followed is not None
    assert "followed by" in followed.group(1)
    assert "20260920T000000Z-alice-partial.lean" in followed.group(1)
    assert f'href="#node={HOLE_IDS[0]}"' in followed.group(1) and "hden" in followed.group(1)
    other = re.search(rf'<li class="outline" data-annex="{OTHER}">(.*?)</li>', body, re.S)
    assert other is not None and "not followed by any merged decomposition" in other.group(1)


def test_outline_text_is_contributor_text_and_escaped(tmp_path: Path) -> None:
    body = panel(page_of(two_outlines(tmp_path)), ROOT_NODE)
    assert "<script>alert(1)</script>" not in body
    assert "Another route &lt;script&gt;" in body
    assert "untrusted" in body.lower()


def test_a_stepped_outline_is_a_checklist(tmp_path: Path) -> None:
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    digest = outline_annex(root, "hden", "combine")
    merged_partial(root, 7, ["hden"], annex=None)
    partial = nodes_dir(root) / ROOT_NODE / "attempts" / "20260920T000000Z-alice-partial.lean"
    partial.write_text(f"theorem x : True := by\n  -- annex: {digest}\n  sorry\n")
    body = panel(page_of(root), ROOT_NODE)
    steps = re.search(r'<ol class="outline-steps">(.*?)</ol>', body, re.S)
    assert steps is not None
    items = re.findall(r"<li[^>]*>(.*?)</li>", steps.group(1), re.S)
    assert len(items) == 2
    assert "hden" in items[0] and f'href="#node={HOLE_IDS[0]}"' in items[0]
    assert "combine" in items[1] and "carried by the assembly" in items[1]
    assert "not that the Lean says what the prose says" in body


def test_the_key_names_the_outline_mark(tmp_path: Path) -> None:
    page = page_of(two_outlines(tmp_path))
    key = re.search(r'<div class="dag-legend">(.*?)</div>', page, re.S)
    assert key is not None and "has an outline" in key.group(1)
    bare = page_of(copy_graph(tmp_path / "bare", publish=True))
    key = re.search(r'<div class="dag-legend">(.*?)</div>', bare, re.S)
    assert key is not None and "has an outline" not in key.group(1)
