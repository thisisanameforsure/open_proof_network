"""F34-T50 (ROUND-2 D4): on a phone, a row of route buttons under the picker.

The picker's numbered ends must fit a 390px screen, so each is about 16px to touch (F34-T40's
limit). Under the picker there is now one 44px button per route ("1 2 3 4"), which draws its route
just as its numbered end does; the one drawn is filled. With harder routes shown their buttons
join the row, which wraps or scrolls inside its own box, never the page. A wide screen does not
show the row.

The browser half runs with Playwright (not part of ``make verify``).
"""

from __future__ import annotations

import re
from html import unescape
from pathlib import Path

from harness import TARGET
from test_f34_drawn_below import ends
from test_one_view import browser
from test_one_view_dominated import harder_tree
from test_routes_view import render_tree, two_routes

PAGE = f"problems/{TARGET}/index.html"
CSS = (Path(__file__).resolve().parents[1] / "opn_site" / "static" / "site.css").read_text()
BUTTON = re.compile(
    r'<button type="button" class="route-btn[^"]*" data-view="([^"]+)" '
    r'aria-pressed="(true|false)"( data-harder="true" hidden)?[^>]*>(\d+)</button>'
)


def test_one_button_per_route_under_the_picker(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path / "g"))[PAGE]
    row = re.search(
        r'<div class="route-buttons" role="group" aria-label="Routes">(.*?)</div>', page, re.S
    )
    assert row is not None
    found = BUTTON.findall(row.group(1))
    assert [unescape(v) for v, _p, _h, _n in found] == list(ends(page))
    assert [n for _v, _p, _h, n in found] == ["1", "2"]
    home = re.search(r'<svg class="dag" data-home="([^"]+)"', page)
    assert home is not None
    assert [unescape(v) for v, pressed, _h, _n in found if pressed == "true"] == [
        unescape(home.group(1))
    ]
    assert page.index('<svg class="selector"') < page.index('class="route-buttons"')
    assert page.index('class="route-buttons"') < page.index('id="sets-list"')


def test_a_harder_routes_button_waits_for_the_harder_routes(tmp_path: Path) -> None:
    page = render_tree(harder_tree(tmp_path / "g"))[PAGE]
    found = BUTTON.findall(page)
    assert [(n, bool(h)) for _v, _p, h, n in found] == [("1", False), ("2", True)]
    assert unescape(found[1][0]).startswith("hard/")


def test_the_row_is_a_phones() -> None:
    assert re.search(r"^\.route-buttons \{[^}]*display: none", CSS, re.M)
    phone = re.findall(r"@media \(max-width: 760px\) \{(.*?)\n\}", CSS, re.S)
    rules = "".join(phone)
    assert re.search(r"\.route-buttons \{[^}]*display: flex[^}]*overflow-x: auto", rules)
    assert re.search(r"\.route-btn \{[^}]*min-width: 44px[^}]*min-height: 44px", rules)


def test_on_a_phone_a_button_draws_its_route(tmp_path: Path) -> None:
    state = """() => ({
      view: document.querySelector('svg.dag').dataset.view,
      buttons: [...document.querySelectorAll('.route-btn')].filter(b => b.checkVisibility())
        .map(b => {
        const r = b.getBoundingClientRect();
        return {n: b.textContent, w: r.width, h: r.height, on: b.getAttribute('aria-pressed'),
                view: b.dataset.view};
      }),
      wide: document.documentElement.scrollWidth,
    })"""
    with browser(harder_tree(tmp_path / "g"), tmp_path / "site") as pg:
        desk = pg.evaluate(state)
        assert desk["buttons"] == [], "a wide screen has no row"
        pg.set_viewport_size({"width": 390, "height": 900})
        pg.wait_for_timeout(300)
        start = pg.evaluate(state)
        assert [b["n"] for b in start["buttons"]] == ["1"]
        assert all(b["w"] >= 44 and b["h"] >= 44 for b in start["buttons"]), start
        assert start["buttons"][0]["on"] == "true" and start["wide"] <= 390
        pg.locator("button.harder-link").click()
        pg.wait_for_timeout(300)
        more = pg.evaluate(state)
        assert [b["n"] for b in more["buttons"]] == ["1", "2"] and more["wide"] <= 390
        pg.locator('.route-btn[data-harder="true"]').click()
        pg.wait_for_function(
            "v => document.querySelector('svg.dag').dataset.view === v",
            arg=more["buttons"][1]["view"],
        )
        drawn = pg.evaluate(state)
        assert [b["on"] for b in drawn["buttons"]] == ["false", "true"]
