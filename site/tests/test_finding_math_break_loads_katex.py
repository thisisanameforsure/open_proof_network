"""F04-T62 (Q60): a page whose only math is a ``.math-break`` claim loads KaTeX.

Seen live on F32-T9's hole, variant-93e79cb5--h3 (2026-10-30): its claim, the gloss's opening
``$$…$$`` written by F04-T51 as ``<span class="math math-break">``, was shown as raw TeX, because
the node page and the page frame both asked ``'class="math"' in body``, a substring a second class
defeats. A page carrying any plain ``.math`` element loaded KaTeX by luck (erdos-68--h1 has 83), so
only a statement whose words are its claim alone showed the defect. The 2026-10-20 erdos-257 bug
list had named it ("has_math substring"). math.js renders every ``.math`` element, so the rule is
the class token, not the attribute text.
"""

from __future__ import annotations

from pathlib import Path

from harness import TARGET
from test_decompositions import HOLE_IDS
from test_finding_panel_math_wrap import wrap_tree
from test_outline_links import page_of

from opn_site import render

KATEX = '<script src="/vendor/katex/katex.min.js"></script>'


def test_a_node_page_whose_only_math_is_a_math_break_claim_loads_katex(tmp_path: Path) -> None:
    page = page_of(wrap_tree(tmp_path), f"nodes/{TARGET}/{HOLE_IDS[1]}/index.html")
    assert '<span class="math math-break">' in page, "the fixture's claim is no longer math-break"
    assert 'class="math"' not in page, "the page carries plain math, so it cannot show the defect"
    assert KATEX in page and render.MATH_HEAD in page


def test_the_page_frame_counts_a_math_element_with_other_classes() -> None:
    frame = render.Renderer.math_frame('<p><span class="math math-break">$x$</span></p>')
    assert frame == {"head": render.MATH_HEAD, "script": render.MATH_SCRIPTS}


def test_a_class_that_merely_starts_with_math_is_not_math() -> None:
    assert render.Renderer.math_frame('<p class="mathematician">Ada</p>') == {}
    assert render.Renderer.math_frame('<p class="cue">no math</p>') == {}
