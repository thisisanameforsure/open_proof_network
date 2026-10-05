"""A file link may break anywhere (found live 2026-10-05).

An annex's path ends in a 64-character hash, and the link to it (``render.file_link``'s
``a.file``) had no wrap rule of its own, so on a 390 px phone the node page of
``euclid-primes/infinitude-of-primes`` was 619 px wide and ``erdos-1050--h1-v2``'s 611 px: the
whole page scrolled sideways. The fixture site's measurements never saw it, because no fixture
annex sat where its link was unclipped. Setting the property on each link in the live page took
both to 390 px.
"""

from __future__ import annotations

import re
from pathlib import Path

CSS = Path(__file__).resolve().parents[1] / "opn_site" / "static" / "site.css"


def test_a_file_link_may_break_anywhere() -> None:
    css = re.sub(r"/\*.*?\*/", "", CSS.read_text(encoding="utf-8"), flags=re.S)
    rules = re.findall(r"([^{}]+)\{([^}]*)\}", css)
    wrapped = [
        body
        for selector, body in rules
        if any(s.strip() == "a.file" for s in selector.split(","))
        and re.search(r"overflow-wrap\s*:\s*anywhere", body)
    ]
    assert wrapped, "no a.file rule with overflow-wrap: anywhere in site.css"
