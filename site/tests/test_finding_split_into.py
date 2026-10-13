"""F04-T46, T47 (Q45, Q46): how a statement was split, at the top of its panel.

A mathematician reading erdos-1094--h2's panel could not tell that the statement had been split,
into what, or by which file: the only trace was a line under "Outlines" naming the partial and the
holes' ids. Now a node with a merged partial proof (a ``decompositions`` entry in ``graph.json``)
opens its panel with a "Split into" block per decomposition — the partial's file, that it merged
and its attestation, then one row per hole: its name, the child as an in-page link, the child's
state, and what the child says, as its statement gloss's opening math when the gloss opens with
math and as its Lean declaration otherwise. Each child's panel names the parent it came from.
T47 (``test_finding_split_lean.py``): the partial's Lean, folded in the block.
"""

from __future__ import annotations

import re
from pathlib import Path

import gloss_fixture as gf
from harness import copy_graph
from test_decompositions import HOLE_IDS, add_hole, merged_partial
from test_outline_links import page_of, panel
from test_products import ROOT_NODE, nodes_dir

PARTIAL_NAME = "20260920T000000Z-alice-partial.lean"
#: The child's gloss opens with its statement in LaTeX, then says more (F20-T16's contract).
MATH_GLOSS = "$p \\land q \\to q \\land p$\n\nEvery conjunction can be read the other way round."
PARTIAL_TEXT = (
    "import Nodes.«and-swap-reassoc».Context\n\n"
    "/-! A partial proof: the module doc the panel leaves out. -/\n\n"
    "theorem x : True := by\n  have hden : True := by sorry\n  have hrem : True := by sorry\n"
    "  exact hden\n"
)


def split_tree(tmp_path: Path) -> Path:
    """The root split by one merged partial into two holes; the first hole's gloss opens with
    math, the second has no gloss."""
    root = copy_graph(tmp_path, publish=True)
    add_hole(root, HOLE_IDS[0], "hden")
    add_hole(root, HOLE_IDS[1], "hrem")
    merged_partial(root, 7, ["hden", "hrem"], annex=None)
    (nodes_dir(root) / ROOT_NODE / "attempts" / PARTIAL_NAME).write_text(
        PARTIAL_TEXT, encoding="utf-8"
    )
    gf.gloss(root, MATH_GLOSS, kind="statement", node=HOLE_IDS[0], author="alice")
    (nodes_dir(root) / ROOT_NODE / "annex" / f"{'d' * 64}.md").write_text(
        "A note on the split.\n", encoding="utf-8"
    )
    return root


def split_block(body: str) -> str:
    m = re.search(r'<section class="split-into".*?</section>', body, re.S)
    assert m is not None, "no Split into block"
    return m.group(0)


def test_the_split_block_opens_the_panel(tmp_path: Path) -> None:
    body = panel(page_of(split_tree(tmp_path)), ROOT_NODE)
    block = split_block(body)
    assert "Split into" in block
    assert PARTIAL_NAME in block and "merged" in block
    assert "attestation" in block and "000007" in block
    # F04-T48 (Q47): in the panel's "How it is being proved", after what is claimed and before
    # what is known (the notes); the outlines' full list is in the record details, after it.
    how = body.index('data-section="how"')
    assert body.index('data-section="claim"') < how < body.index('<section class="split-into"')
    assert body.index('<section class="split-into"') < body.index('data-section="known"')
    assert body.index('<section class="split-into"') < body.index("panel-outlines")


def test_each_hole_is_a_row_with_its_name_link_state_and_statement(tmp_path: Path) -> None:
    block = split_block(panel(page_of(split_tree(tmp_path)), ROOT_NODE))
    rows = re.findall(r'<li class="split-hole"[^>]*>(.*?)</li>', block, re.S)
    assert len(rows) == 2
    first, second = rows
    assert "<code>hden</code>" in first and f'href="#node={HOLE_IDS[0]}"' in first
    assert "dot-" in first  # the child's state, with its dot
    # The gloss opens with math: its first block, rendered for KaTeX, not the gloss's later text.
    assert "p \\land q \\to q \\land p" in first and 'class="math' in first
    assert "the other way round" not in first
    # No gloss on the second hole: its Lean declaration instead.
    assert "<code>hrem</code>" in second and f'href="#node={HOLE_IDS[1]}"' in second
    assert '<pre class="lean' in second and "theorem" in second


def test_a_gloss_that_does_not_open_with_math_gives_way_to_the_lean(tmp_path: Path) -> None:
    root = split_tree(tmp_path)
    gf.gloss(root, "In words only: nothing here is math.", kind="statement", node=HOLE_IDS[1])
    block = split_block(panel(page_of(root), ROOT_NODE))
    second = re.findall(r'<li class="split-hole"[^>]*>(.*?)</li>', block, re.S)[1]
    assert "In words only" not in second
    assert '<pre class="lean' in second


def test_a_hole_names_the_parent_it_came_from(tmp_path: Path) -> None:
    page = page_of(split_tree(tmp_path))
    body = panel(page, HOLE_IDS[0])
    line = re.search(r'<p class="hole-of">(.*?)</p>', body, re.S)
    assert line is not None
    assert "<code>hden</code>" in line.group(1)
    assert f'href="#node={ROOT_NODE}"' in line.group(1)
    assert PARTIAL_NAME in line.group(1)
    # Before the Lean, so a reader at the hole sees where it came from first.
    assert body.index('<p class="hole-of">') < body.index('<pre class="lean statement')


def test_two_decompositions_are_two_blocks(tmp_path: Path) -> None:
    root = split_tree(tmp_path)
    later = "attempts/20260924T000000Z-bob-partial.lean"
    merged_partial(root, 9, ["hrem"], path=later, annex=None)
    body = panel(page_of(root), ROOT_NODE)
    assert body.count('<section class="split-into"') == 2


def test_a_node_without_a_merged_partial_has_no_split_block(tmp_path: Path) -> None:
    body = panel(page_of(copy_graph(tmp_path, publish=True)), ROOT_NODE)
    assert "split-into" not in body and 'class="hole-of"' not in body


def test_hole_statement_text_is_escaped(tmp_path: Path) -> None:
    root = split_tree(tmp_path)
    gf.gloss(root, "$x$ <script>alert(1)</script>", kind="statement", node=HOLE_IDS[1])
    block = split_block(panel(page_of(root), ROOT_NODE))
    assert "<script>alert(1)</script>" not in block
