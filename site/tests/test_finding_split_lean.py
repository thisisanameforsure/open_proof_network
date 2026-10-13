"""F04-T47 (Q46): the partial proof's Lean, folded inside its "Split into" block.

A reader who wants to see how the holes are put back together had to leave the page for the
record host. The block now carries the merged partial's text from its theorem line on (the same
trim the statement panel uses, ``render.declaration_only``), closed by default, with its link.
"""

from __future__ import annotations

import re
from pathlib import Path

from harness import TARGET
from test_finding_split_into import PARTIAL_NAME, split_block, split_tree
from test_outline_links import page_of, panel
from test_products import ROOT_NODE


def test_the_partial_lean_is_folded_in_the_block(tmp_path: Path) -> None:
    block = split_block(panel(page_of(split_tree(tmp_path)), ROOT_NODE))
    fold = re.search(r'<details class="split-lean">(.*?)</details>', block, re.S)
    assert fold is not None, "no folded partial"
    assert "Read the partial proof (Lean)" in fold.group(1)
    assert "<details open" not in block
    lean = re.search(r'<pre class="lean">(.*?)</pre>', fold.group(1), re.S)
    assert lean is not None
    assert lean.group(1).startswith("theorem x : True := by")
    assert "have hden" in lean.group(1)
    assert "import " not in lean.group(1) and "module doc" not in lean.group(1)
    assert f"{TARGET}/nodes/{ROOT_NODE}/attempts/{PARTIAL_NAME}" in fold.group(1)  # its link
