"""F34-T31 (REMINDERS-erdos-257 item 12): the drawing's developer caption ("labels drop the
problem's own name (a pill's title has its full id); hover a statement …") is gone; the one hint
left is the reader's: "Select a statement to see its record."
"""

from __future__ import annotations

import re
from pathlib import Path

from harness import TARGET
from test_routes_view import render_tree, two_routes


def test_the_caption_is_one_plain_hint(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path / "g"))[f"problems/{TARGET}/index.html"]
    assert "labels drop the problem" not in page and "full id" not in page
    caption = re.findall(r'<p class="dag-caption">(.*?)</p>', page, re.S)
    assert caption == ["Select a statement to see its record."], caption
