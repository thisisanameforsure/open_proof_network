"""F34-T53 (ROUND-2 "Done means", the owner 2026-11-27: "yes do matching"): §1 is laid out as
``New-Erdos257`` and ``New-Erdos257-List`` draw it.

* Two cards, one above the other. The first is the picker: "Routes" with a Tree | List switch at
  its right, the tree or the list, one line saying what a numbered end is, and "Drawn below"
  under a rule. The second is Figure 1: its kicker, the route's name with its count, the fold
  and retire controls, and the drawing. Before this both sat in one card under "Key to the
  drawing" and a row of underlined tabs.
* The selected side of the switch is filled with ink.
* §1 opens with the mockup's sentence about routes; under the figure's card the caption reads
  "Figure 1. The selected route as a tree: …", and the key to the drawing folds under it.
* The main picker's behaviour is unchanged (the owner: "dont touch main picker").

The browser half runs with Playwright (not part of ``make verify``).
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from harness import TARGET
from test_one_view import browser
from test_routes_view import render_tree, two_routes

from opn_site import render

PAGE = f"problems/{TARGET}/index.html"
VOID = frozenset(
    {"br", "img", "input", "meta", "link", "hr", "wbr", "path", "circle", "rect", "line", "use"}
)


class _Where(HTMLParser):
    """For each element, the classes of the elements it sits inside."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, tuple[str, ...]]] = []
        self.inside: dict[str, set[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        cls = tuple((dict(attrs).get("class") or "").split())
        above = {c for _t, cs in self.stack for c in cs}
        for c in cls:
            self.inside.setdefault(c, set()).update(above)
        ident = dict(attrs).get("id")
        if ident:
            self.inside.setdefault("#" + ident, set()).update(above)
        if tag not in VOID:
            self.stack.append((tag, cls))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return


def inside(page: str) -> dict[str, set[str]]:
    p = _Where()
    p.feed(page)
    return p.inside


def test_the_picker_and_the_figure_are_two_cards(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path / "g"))[PAGE]
    at = inside(page)
    for cls in ("picker-head", "route-tabs", "selector", "#sets-list", "drawn-below"):
        assert "picker-card" in at[cls], cls
        assert "figure-card" not in at[cls], cls
    for cls in ("figure-cap", "figure-folds", "dag-scroll"):
        assert "figure-card" in at[cls], cls
        assert "picker-card" not in at[cls], cls
    # neither card sits inside another card
    assert "card" not in at["picker-card"] and "card" not in at["figure-card"]
    assert page.index('class="picker-card') < page.index('class="figure-card')


def test_the_picker_is_headed_routes_with_the_switch_beside_it(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path / "g"))[PAGE]
    head = re.search(r'<div class="picker-head">(.*?)</div>\s*<div id="sets-tree"', page, re.S)
    assert head is not None
    assert '<h3 class="picker-title">Routes</h3>' in head.group(1)
    assert 'class="route-tabs"' in head.group(1)
    assert "Ways to settle the problem" not in page


def test_the_figures_heading_carries_the_count(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path / "g"))[PAGE]
    below = re.search(r'<p class="drawn-below">Drawn below ↓ <strong>(.*?)</strong>', page)
    cap = re.search(r'<p class="figure-cap">.*?<strong>(.*?)</strong>', page, re.S)
    assert below is not None and cap is not None
    assert cap.group(1) == below.group(1)
    assert re.search(r"\d+ statements?, \d+ open$", cap.group(1))


def test_the_words_are_the_mockups(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path / "g"))[PAGE]
    assert (
        "The problem is taken apart into Lean statements along routes: each route is a set of "
        "statements that would settle it. Choose a route to draw it as a tree; select any "
        "statement to read it in the panel." in page
    )
    hint = re.search(r'<p class="picker-hint">(.*?)</p>', page, re.S)
    assert hint is not None
    assert "Each numbered end is a route" in hint.group(1)
    assert "would disprove it" not in hint.group(1), "no route here disproves the problem"
    caption = re.search(r'<p class="dag-caption">(.*?)</p>', page, re.S)
    assert caption is not None
    assert caption.group(1).startswith("<strong>Figure 1.</strong> The selected route as a tree")
    # the key to the drawing is still on the page, folded, under the caption (ROUND-2 D6.3)
    assert page.index('class="dag-caption"') < page.index('<details class="dag-key"')
    assert page.index('class="figure-card') < page.index('class="dag-caption"')


def test_a_route_that_would_disprove_is_named_in_the_hint() -> None:
    """The page asks for the rust sentence when its list has a disproving row."""
    assert "would disprove it" not in render.picker_hint(refutes=False)
    both = render.picker_hint(refutes=True)
    assert "Each numbered end is a route" in both and "would disprove it" in both


def test_the_switch_is_filled_and_the_cards_stand_apart(tmp_path: Path) -> None:
    state = """() => {
      const box = s => document.querySelector(s).getBoundingClientRect();
      const css = (s, p) => getComputedStyle(document.querySelector(s))[p];
      const picker = box('.picker-card'), figure = box('.figure-card');
      const title = box('.picker-title'), tabs = box('.route-tabs');
      return {
        on: css('.route-tabs button[aria-selected="true"]', 'backgroundColor'),
        off: css('.route-tabs button[aria-selected="false"]', 'backgroundColor'),
        ink: getComputedStyle(document.documentElement).getPropertyValue('--ink').trim(),
        onColor: css('.route-tabs button[aria-selected="true"]', 'color'),
        gap: figure.top - picker.bottom,
        sameRow: Math.abs((title.top + title.bottom) / 2 - (tabs.top + tabs.bottom) / 2) < 12,
        tabsRight: picker.right - tabs.right,
        pickerBorder: css('.picker-card', 'borderTopWidth'),
        figureBorder: css('.figure-card', 'borderTopWidth'),
        wrapBorder: css('.dag-wrap', 'borderTopWidth'),
        cap: document.querySelector('.figure-cap strong').textContent,
        below: document.querySelector('.drawn-below strong').textContent,
        view: document.querySelector('svg.dag').dataset.view,
        wide: document.documentElement.scrollWidth,
      };
    }"""
    with browser(two_routes(tmp_path / "g"), tmp_path / "site") as pg:
        s = pg.evaluate(state)
        assert s["on"] != s["off"] and s["on"] not in ("rgba(0, 0, 0, 0)", "transparent"), s
        assert s["gap"] >= 8, s
        assert s["sameRow"] and 0 <= s["tabsRight"] <= 40, s
        assert s["pickerBorder"] == "1px" and s["figureBorder"] == "1px", s
        assert s["wrapBorder"] == "0px", s
        assert s["cap"] == s["below"], s
        # drawing another route rewrites both lines alike
        other = pg.evaluate(
            """() => [...document.querySelectorAll('svg.selector g.kind-leaf')]
                 .map(g => g.dataset.view)"""
        )
        target = next(v for v in other if v != s["view"])
        pg.locator(f'svg.selector g.kind-leaf[data-view="{target}"]').click()
        pg.wait_for_function(
            "v => document.querySelector('svg.dag').dataset.view === v", arg=target
        )
        after = pg.evaluate(state)
        assert after["cap"] == after["below"] != s["cap"], after
        # the List side
        pg.locator('.route-tabs [aria-controls="sets-list"]').click()
        pg.wait_for_timeout(200)
        lst = pg.evaluate(state)
        assert lst["on"] == s["on"] and lst["gap"] >= 8, lst
        pg.set_viewport_size({"width": 390, "height": 900})
        pg.wait_for_timeout(300)
        phone = pg.evaluate(state)
        assert phone["wide"] <= 390 and phone["gap"] >= 8 and phone["sameRow"], phone
