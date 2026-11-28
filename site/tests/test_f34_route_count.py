"""F34-T46 (ROUND-2 D3): Figure 1 draws only its route, and says how many statements that is.

* The count a numbered end carries ("19 statements, 2 open") is the number of statement boxes its
  route draws: the statements still to prove, the proved ones, and the statements the route
  splits on the way (the problem's own among them). A fold of proved statements counts for the
  statements it holds. Before this the count left out every statement the route splits, so the
  caption said 8 over a drawing of 19 boxes (live erdos-1094, 2026-11-27).
* The line under the figure's caption names the splits a steward or curator may retire by their
  words; it carries no raw route id (``erdos-1094@1 erdos-1094--h2@1 …`` was eleven lines on a
  phone).
"""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Any

from harness import TARGET
from test_f34_drawn_below import ends
from test_f34_folds import proved_pair
from test_routes_view import render_tree, two_routes
from test_shelving_controls import (  # noqa: F401 — the shelving test's site and fake service
    FakeService,
    pages,
    site,
)

PAGE = f"problems/{TARGET}/index.html"


def layouts_of(page: str) -> dict[str, Any]:
    m = re.search(r'<script type="application/json" id="graph-layouts">(.*?)</script>', page, re.S)
    assert m is not None
    doc: dict[str, Any] = json.loads(m.group(1).replace("<\\/", "</"))
    return doc


def boxes(page: str, view: str) -> int:
    """The statement boxes ``view`` draws: every node that is no route's junction, a fold box
    counted for the statements it holds (its words in the drawing say how many)."""
    lay = layouts_of(page)[view]
    junctions = set(re.findall(r'<g class="junction[^"]*" data-route="([^"]+)"', page))
    total = 0
    for nid in lay["nodes"]:
        if unescape(nid) in {unescape(j) for j in junctions}:
            continue
        if nid.startswith("fold:"):
            words = re.search(
                rf'data-node="{re.escape(nid)}"[^>]*aria-label="(\d+) proved statements', page
            )
            assert words is not None, nid
            total += int(words.group(1))
        else:
            total += 1
    return total


def check(page: str) -> None:
    named = ends(page)
    assert named
    for view, (_route, count) in named.items():
        said = re.match(r"(\d+) statements?, (\d+) open$", count)
        assert said is not None, count
        assert int(said.group(1)) == boxes(page, view), (view, count, boxes(page, view))


def test_the_caption_counts_the_boxes_the_route_draws(tmp_path: Path) -> None:
    check(render_tree(two_routes(tmp_path / "g"))[PAGE])


def test_a_fold_counts_for_the_statements_it_holds(tmp_path: Path) -> None:
    page = render_tree(proved_pair(two_routes(tmp_path / "g")))[PAGE]
    assert any(n.startswith("fold:") for lay in layouts_of(page).values() for n in lay["nodes"])
    check(page)


def test_the_figures_retire_line_carries_no_raw_id(pages: dict[str, str]) -> None:  # noqa: F811
    page = pages[PAGE]
    groups = re.findall(r'<details class="figure-retire"[^>]*>(.*?)</details>', page, re.S)
    assert groups
    for g in groups:
        assert "<code>" not in g, g
        text = unescape(re.sub(r"<[^>]+>", " ", g))
        assert "@" not in text and "--h" not in text and TARGET not in text, text
        assert 'class="retire-act"' not in g or 'data-partial="' in g
