"""F34-T12 (R14; handoff §3.4.2): the routes in a Tree view and a List view, and the drawing
opening on one route — the one that proves the problem with the fewest open statements.

* The drawing names its opening view (``data-home``): the selector's leaf for the proving set
  with the fewest open statements, ties to the fewer statements, then the record's order. A
  problem with no route has none, and opens as today.
* "Tree" and "List" are two tabs over the selector and the sets table, rendered hidden (only the
  script can switch them); without the script both stay on the page.
* The R15 folds (a proved statement's box naming how many it holds) are F34-T24's.
"""

from __future__ import annotations

import re
from pathlib import Path

from harness import TARGET, copy_graph
from test_one_view_markup import layouts_in
from test_routes_view import THIRD, render_tree, two_routes

PAGE = f"problems/{TARGET}/index.html"


def set_rows(page: str) -> list[dict[str, str]]:
    """Each row of the sets table: its set, side, view and the Open column's count."""
    out = []
    for m in re.finditer(
        r'<tr class="set-row side-([a-z]+)" data-set="([^"]+)"[^>]*>(.*?)</tr>', page, re.S
    ):
        view = re.search(r'data-view="([^"]+)"', m.group(0))
        cells = re.findall(r'<td class="num" data-sort="(\d+)"', m.group(3))
        out.append(
            {
                "side": m.group(1),
                "set": m.group(2),
                "view": view.group(1) if view else "",
                "statements": cells[0] if cells else "",
                "open": cells[2] if len(cells) > 2 else "",
            }
        )
    return out


def home_of(page: str) -> str | None:
    m = re.search(r'<svg class="dag"[^>]*\bdata-home="([^"]+)"', page)
    return m.group(1) if m else None


def test_the_drawing_opens_on_the_proving_route_with_the_fewest_open(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path))[PAGE]
    rows = [r for r in set_rows(page) if r["side"] == "proves" and r["view"]]
    assert len(rows) == 2, rows  # guard: two ways to prove the problem
    best = min(rows, key=lambda r: (int(r["open"]), int(r["statements"])))
    home = home_of(page)
    assert home == best["view"], (home, rows)
    # By hand: [h1, h2] leaves two open, [h3] one; the opening route is the one through h3.
    assert THIRD in layouts_in(page)[home]["nodes"]


def test_a_problem_with_no_route_names_no_opening_view(tmp_path: Path) -> None:
    page = render_tree(copy_graph(tmp_path, publish=True))[PAGE]
    assert '<svg class="dag"' in page and home_of(page) is None


def test_tree_and_list_are_two_tabs_over_the_selector_and_the_table(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path))[PAGE]
    tabs = re.search(r'<div class="route-tabs" role="tablist"[^>]*hidden>(.*?)</div>', page, re.S)
    assert tabs is not None
    buttons = re.findall(
        r'<button type="button" role="tab" aria-controls="([a-z-]+)" aria-selected="(true|false)">'
        r"([A-Za-z]+)</button>",
        tabs.group(1),
    )
    assert buttons == [("sets-tree", "true", "Tree"), ("sets-list", "false", "List")]
    assert '<div id="sets-tree"><div class="selector-wrap">' in page
    assert '<div id="sets-list"><div class="sets-grid">' in page


def test_no_tabs_without_routes(tmp_path: Path) -> None:
    page = render_tree(copy_graph(tmp_path, publish=True))[PAGE]
    assert 'class="route-tabs"' not in page
