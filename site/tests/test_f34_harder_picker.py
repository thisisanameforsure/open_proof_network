"""F34-T48 (ROUND-2 D2): the route picker's ends are routes, and the harder routes join it.

The owner, 2026-11-27: "Clicking show harder routes should update the tree view where you select
routes. The selected route view should just show the route selected in the route picker."

* Every end of the picker is a numbered, selectable route. Before this the picker of a route with
  folded proved statements grew a dead-end square per fold: the fold's own layout had been taken
  for a choice point (live erdos-1094: four numbered ends and six squares).
"""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Any

from harness import TARGET
from test_one_view import browser
from test_one_view_dominated import harder_doc, harder_tree
from test_routes_view import node, render_tree

from opn_gate import routes
from opn_site import one_view

PAGE = f"problems/{TARGET}/index.html"


def folded_doc() -> dict[str, Any]:
    """Two routes neither of which needs less than the other, the first with two proved holes
    (a fold) beside its open one."""
    return {
        "schema": "graph/v9",
        "target_id": "t",
        "root": "t",
        "nodes": [
            node("t", origin="authored", routes=[["t--a", "t--b", "t--c"], ["t--d"]]),
            node("t--a", "proved"),
            node("t--b", "proved"),
            node("t--c"),
            node("t--d"),
        ],
    }


def drawn(d: dict[str, Any]) -> one_view.Drawing:
    return one_view.drawing(d, [], href={n["node_id"]: "#" for n in d["nodes"]}, prefix="t")


NODES = re.compile(r'<g class="sel-node (kind-[a-z]+)[^"]*"[^>]*data-key="([^"]+)"')


def leaves(svg: str) -> list[tuple[str, str]]:
    """The picker's ends — nodes no line leaves — as (kind, key)."""
    parents = set(re.findall(r'<path class="sel-edge[^"]*" data-from="([^"]+)"', svg))
    return [(kind, key) for kind, key in NODES.findall(svg) if key not in parents]


def test_every_end_of_the_picker_is_a_numbered_route() -> None:
    picture = drawn(folded_doc())
    assert "fold:" in picture.layouts_json, "the fixture folds"
    ends = leaves(picture.selector)
    assert len(ends) == 2, ends
    assert all(kind == "kind-leaf" for kind, _key in ends), ends
    assert not any("~" in key for _kind, key in NODES.findall(picture.selector)), "a fold's view"


# -- the harder routes join the picker ------------------------------------------------------------
#
# * "Show n harder routes" is a quiet control under the picker. It never changes Figure 1 by
#   itself: it swaps the picker for one that also carries each harder route as a numbered end,
#   numbered after the main ones and drawn lighter, and shows the harder rows of the List under
#   "Harder routes".
# * A harder route is a way of settling the problem that needs strictly more than another (a
#   finest set F27-R14 leaves out), so the count on the control is the number of ends it adds.
#   (The old button counted the *splits* only such ways go through: 35 on erdos-1094, where the
#   ways number 42.)
# * Figure 1 draws exactly one route. The ``harder`` layout, every harder statement at once, is
#   gone.


def test_read_lists_the_harder_sets_after_the_kept_ones_on_request() -> None:
    g = harder_doc()
    kept = routes.read(g, [])
    whole = routes.read(g, [], harder=True)
    assert [s.id for s in whole.sets[: len(kept.sets)]] == [s.id for s in kept.sets]
    assert len(whole.sets) == len(kept.sets) + 1
    extra = whole.sets[-1]
    assert set(extra.open) == {"t--a", "t--b"} and extra.routes == ("t@2",)
    assert routes.read(g, []).as_dict() == kept.as_dict(), "the default reading is unchanged"


def harder_ends(picture: one_view.Drawing) -> list[tuple[str, str, str]]:
    """The harder picker's numbered ends as (number, view, classes)."""
    return [
        (n, unescape(view), cls)
        for cls, view, n in re.findall(
            r'<g class="sel-node (kind-leaf[^"]*)" data-view="([^"]+)"[^>]*>.*?<text[^>]*>(\d+)'
            r"</text>",
            picture.harder_selector,
            re.S,
        )
    ]


def test_the_harder_picker_numbers_every_route_the_harder_ones_last_and_lighter() -> None:
    picture = drawn(harder_doc())
    main = leaves(picture.selector) or NODES.findall(picture.selector)
    assert [kind for kind, _k in main] == ["kind-leaf"], "one kept route"
    assert picture.harder_selector.startswith('<svg class="selector harder-picker"')
    ends = harder_ends(picture)
    assert [n for n, _v, _c in ends] == ["1", "2"]
    kept_view = re.search(
        r'<g class="sel-node kind-leaf[^"]*" data-view="([^"]+)"', picture.selector
    )
    assert kept_view is not None and ends[0][1] == unescape(kept_view.group(1))
    assert "harder" not in ends[0][2].split()
    assert ends[1][1].startswith("hard/") and "harder" in ends[1][2].split()
    assert all(kind == "kind-leaf" for kind, _key in leaves(picture.harder_selector))
    lays = json.loads(
        re.search(r">(.*)</script>", picture.layouts_json, re.S).group(1).replace("<\\/", "</")  # type: ignore[union-attr]
    )
    assert ends[1][1] in lays and "harder" not in lays
    assert {"t", "t--a", "t--b", "t--p"} <= set(lays[ends[1][1]]["nodes"])
    # only an end is pressable in the harder picker: a choice point or a line draws no route
    pressable = re.findall(
        r'<(g|path) class="sel-(node|edge)([^"]*)" data-view=', picture.harder_selector
    )
    assert pressable and all(kind == "g" and "kind-leaf" in cls for kind, _w, cls in pressable)


def test_the_control_is_quiet_and_counts_the_ends_it_adds() -> None:
    picture = drawn(harder_doc())
    assert picture.harder_toggle == (
        '<p class="harder-line" hidden><button type="button" class="harder-link" '
        'aria-pressed="false" data-shown-label="Hide harder route">Show 1 harder route</button>'
        "</p>"
    )
    plain = dict(harder_doc())
    plain["nodes"] = [n for n in plain["nodes"] if n["node_id"] not in ("t--b", "t--p")]
    plain["nodes"][0] = node("t", origin="authored", routes=[["t--a"]])
    quiet = drawn(plain)
    assert quiet.harder_toggle == "" and quiet.harder_selector == ""


def test_the_list_holds_the_harder_rows_under_their_own_heading() -> None:
    picture = drawn(harder_doc())
    block = re.search(
        r'<div class="harder-routes" hidden><h4 class="harder-head">Harder routes</h4>'
        r'<ol class="route-list">(.*?)</ol></div>',
        picture.table,
        re.S,
    )
    assert block is not None
    rows = re.findall(r'<li class="route-row[^>]*>', block.group(1))
    assert len(rows) == 1 and 'data-harder="true"' in rows[0] and 'data-view="hard/' in rows[0]
    assert re.search(r'class="route-n"[^>]*>2</button>', block.group(1))
    head = picture.table[: picture.table.index('<div class="harder-routes"')]
    assert head.count('<li class="route-row') == 1 and "data-harder" not in head


def test_on_the_page_the_control_sits_under_the_picker(tmp_path: Path) -> None:
    page = render_tree(harder_tree(tmp_path / "g"))[PAGE]
    assert "harder-toggle" not in page and "strictly harder routes (" not in page
    assert (
        page.index('id="sets-list"')
        < page.index('class="harder-line"')
        < page.index('class="drawn-below"')
    )
    assert page.index('class="route-tabs"') < page.index('class="harder-line"')


def test_showing_harder_routes_changes_the_picker_never_the_figure(tmp_path: Path) -> None:
    """In a browser (Playwright)."""
    state = """() => ({
      view: document.querySelector('svg.dag').dataset.view,
      main: document.querySelector('svg.selector:not(.harder-picker)').checkVisibility(),
      hard: document.querySelector('svg.selector.harder-picker').checkVisibility(),
      rows: [...document.querySelectorAll('li.route-row')].filter(r => r.checkVisibility()).length,
      boxes: [...document.querySelectorAll('svg.dag g.node:not(.off-view)')].length,
      link: document.querySelector('button.harder-link').textContent,
      below: document.querySelector('.drawn-below').textContent,
    })"""
    with browser(harder_tree(tmp_path / "g"), tmp_path / "site") as pg:
        link = pg.locator("button.harder-link")
        assert link.is_visible() and link.inner_text() == "Show 1 harder route"
        before = pg.evaluate(state)
        assert before["main"] and not before["hard"]
        link.click()
        pg.wait_for_timeout(400)
        shown = pg.evaluate(state)
        assert shown["hard"] and not shown["main"] and shown["link"] == "Hide harder route"
        assert shown["view"] == before["view"] and shown["boxes"] == before["boxes"], "the figure"
        end = pg.locator("svg.harder-picker g.sel-node.harder").first
        view = end.get_attribute("data-view")
        end.click()
        pg.wait_for_function("v => document.querySelector('svg.dag').dataset.view === v", arg=view)
        on_hard = pg.evaluate(state)
        assert on_hard["below"].startswith("Drawn below ↓ Route 2")
        pg.locator('.route-tabs [aria-controls="sets-list"]').click()
        assert pg.evaluate(state)["rows"] == 2
        link.click()
        pg.wait_for_function(
            "v => document.querySelector('svg.dag').dataset.view === v", arg=before["view"]
        )
        hidden = pg.evaluate(state)
        assert hidden["rows"] == 1 and hidden["link"] == "Show 1 harder route"
