"""F34-T44 (REMINDERS-erdos-257 item 18; handoff §3.4.4): a §2 group's heading names the statement
the group was proposed for by its words, and the routes it lies on — 'For "…" (Route 2)' — not its
id ("Proposed for erdos-257--h18"). A statement on every route (the problem's own) names no route.
"""

from __future__ import annotations

import re
from pathlib import Path

from harness import TARGET
from test_crux_band import band_tree
from test_products import ROOT_NODE
from test_routes_view import render_tree

from opn_site import render


def test_the_heading_words_and_routes() -> None:
    link = '<a href="/x/">bounded k</a>'
    assert render.group_heading(link, []) == f"For &ldquo;{link}&rdquo;"
    assert render.group_heading(link, ["Route 2"]) == f"For &ldquo;{link}&rdquo; (Route 2)"
    assert (
        render.group_heading(link, ["Route 2", "Route 5"])
        == f"For &ldquo;{link}&rdquo; (Routes 2, 5)"
    )


def test_a_group_for_the_problem_names_it_by_its_words(tmp_path: Path) -> None:
    page = render_tree(band_tree(tmp_path / "g"))[f"problems/{TARGET}/index.html"]
    heads = re.findall(r'<div class="off-group"[^>]*><h3>(.*?)</h3>', page, re.S)
    assert heads, "the fixture has a proposed group"
    assert all(h.startswith("For &ldquo;") for h in heads), heads
    assert "Proposed for" not in "".join(heads)
    assert f'href="/nodes/{TARGET}/{ROOT_NODE}/"' in heads[0]
    assert "(Route" not in heads[0], "the problem's own statement is on every route"
