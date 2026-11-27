"""F34-T51 (ROUND-2 D8): on a phone the outline starts with the problem, and a statement's name
shows once.

Before this, on a phone the problem's own record opened under its row as the page loaded: a dark
bar with the problem's name, the dark "Selected in Figure 1" header with the same name under it,
and about 1500px of record before the next row of the outline (live erdos-1094, 2026-11-27), so
the outline read as starting at "Fixed k: …".

* As the page opens, the outline lists the route from the problem's own row down; no record is
  open (the problem's statement is the page's headline).
* Tapping a row opens its record directly under it (REMINDERS item 22, unchanged); the row's own
  bar gives way to the record's dark header, so the name shows once.
* Tapping that header closes the record and the row is back.
* A wide screen is unchanged: the problem's record is beside the drawing as the page opens.

Runs with Playwright (not part of ``make verify``).
"""

from __future__ import annotations

from pathlib import Path

from test_decompositions import HOLE_IDS
from test_one_view import browser
from test_products import ROOT_NODE
from test_routes_view import two_routes

STATE = """() => {
  const vis = e => !!e && e.checkVisibility();
  const rows = [...document.querySelectorAll('ol.route-outline > li[data-node]')].filter(vis);
  const open = [...document.querySelectorAll('.panel[data-node]')].filter(p => !p.hidden && vis(p));
  return {
    rows: rows.map(li => li.dataset.node),
    rowLinks: rows.filter(li => vis(li.querySelector(':scope > a[data-node]')))
      .map(li => li.dataset.node),
    open: open.map(p => p.dataset.node),
    under: open.map(p => (p.parentElement.dataset || {}).node || null),
    heads: open.map(p => vis(p.querySelector('.panel-head'))),
  };
}"""


def test_the_outline_starts_with_the_problem_and_nothing_is_open(tmp_path: Path) -> None:
    with browser(two_routes(tmp_path / "g"), tmp_path / "site") as pg:
        wide = pg.evaluate(STATE)
        assert wide["open"] == [ROOT_NODE], "a wide screen opens on the problem's record"
        pg.set_viewport_size({"width": 390, "height": 900})
        pg.reload()
        pg.wait_for_timeout(600)
        start = pg.evaluate(STATE)
    assert start["rows"] and start["rows"][0] == ROOT_NODE
    assert start["rowLinks"] == start["rows"], "every row is its own plain row"
    assert start["open"] == [], start


def test_a_tapped_rows_name_shows_once_and_its_header_closes_it(tmp_path: Path) -> None:
    with browser(two_routes(tmp_path / "g"), tmp_path / "site", view="routes") as pg:
        pg.set_viewport_size({"width": 390, "height": 900})
        pg.reload()
        pg.wait_for_timeout(600)
        hole = HOLE_IDS[0]
        pg.locator(f'ol.route-outline > li[data-node="{hole}"] > a[data-node]').click()
        pg.wait_for_timeout(300)
        opened = pg.evaluate(STATE)
        pg.locator(f'ol.route-outline > li[data-node="{hole}"] .panel-head').click()
        pg.wait_for_timeout(300)
        closed = pg.evaluate(STATE)
    assert opened["open"] == [hole] and opened["under"] == [hole] and opened["heads"] == [True]
    assert hole not in opened["rowLinks"], "the row's bar gives way to the record's header"
    assert hole in opened["rows"]
    assert closed["open"] == [] and hole in closed["rowLinks"]
