"""F34-T47 (ROUND-2 D1; mockup ``New-Erdos257-List``): the List view is one row per route, not a
table.

The owner, 2026-11-27: "Drop the table. Keep what is shown in the problems design." This
replaces F27's sets table (Set, Statements, Proved, Open, Shared, Assemblies, Routes; "Fewest open
first") and F31-Q18's Routes column.

* One row per numbered end of the picker, in its order: the route's number in a circle (rust for a
  route that would disprove the problem), its name, "proves the problem · n statements · p proved
  · s split further · k open" (the counts add up), "through <statement>, split by <who>", and
  Draw · Statements (and Retire for a steward or curator, on a build with a service).
* The row of the route drawn is marked; no row is ever hidden. "Drawn below ↓" stays under the
  list, above the figure.
* Figure 1's heading carries "Proved statements folded · unfold" when the route folds any, and
  the route has a layout with every fold open.

The browser half runs with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest site/tests/test_f34_route_list.py``
"""

from __future__ import annotations

import functools
import http.server
import re
import socketserver
import threading
from collections.abc import Iterator
from html import unescape
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET
from test_f34_drawn_below import ends
from test_f34_folds import proved_pair
from test_f34_route_count import layouts_of
from test_routes_view import render_tree, two_routes
from test_shelving_controls import (  # noqa: F401 — the shelving test's site and fake service
    FakeService,
    pages,
    site,
    static_pages,
)

from opn_site import render

PAGE = f"problems/{TARGET}/index.html"
ROW = re.compile(r'<li class="route-row side-([a-z]+)"([^>]*)>(.*?)</li><!-- /route-row -->', re.S)


def rows(page: str) -> list[tuple[str, str, str]]:
    return [(m.group(1), m.group(2), m.group(3)) for m in ROW.finditer(page)]


@pytest.fixture(scope="module")
def tree(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    return render_tree(two_routes(tmp_path_factory.mktemp("f34-route-list") / "g"))


@pytest.fixture(scope="module")
def folded(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    return render_tree(proved_pair(two_routes(tmp_path_factory.mktemp("f34-route-list-f") / "g")))


def test_the_sets_table_is_gone(tree: dict[str, str]) -> None:
    page = tree[PAGE]
    for gone in ("routes-table", "routes-fewest", "Fewest open first", "set-swatch", "set-row"):
        assert gone not in page, gone
    assert "<th" not in page[page.index('id="sets-list"') : page.index('class="figure-cap"')]


def test_one_row_per_route_in_the_pickers_order(tree: dict[str, str]) -> None:
    page = tree[PAGE]
    named = ends(page)
    found = rows(page)
    views = [unescape(re.search(r'data-view="([^"]+)"', attrs).group(1)) for _s, attrs, _b in found]  # type: ignore[union-attr]
    assert views == list(named), (views, list(named))
    for k, (side, _attrs, body) in enumerate(found, start=1):
        assert side == "proves"
        n = re.search(r'<button type="button" class="route-n"[^>]*>(\d+)</button>', body)
        assert n is not None and int(n.group(1)) == k
        name = re.search(r'<span class="route-name">([^<]+)</span>', body)
        assert name is not None and name.group(1).strip()
        counts = re.search(
            r'<span class="route-counts">proves the problem · (\d+) statements? · (\d+) proved · '
            r'(?:<span title="[^"]*">(\d+) split further</span> · )?'
            r"<strong>(\d+) open</strong></span>",
            body,
        )
        assert counts is not None, body
        total, proved, split, open_ = (int(x or 0) for x in counts.groups())
        assert total == proved + split + open_
        said = ends(page)[views[k - 1]][1]
        assert said == f"{total} statement{'' if total == 1 else 's'}, {open_} open"
        assert re.search(r'<span class="route-through">through <code>[^<]+</code>', body), body
        assert 'class="route-draw"' in body
        listed = re.search(
            r'<details class="route-statements"><summary>Statements</summary>(.*?)'
            r"</details>",
            body,
            re.S,
        )
        assert listed is not None and f'href="/nodes/{TARGET}/' in listed.group(1)
        assert "@" not in unescape(re.sub(r"<[^>]+>", " ", body)), body


def test_the_drawn_routes_row_is_marked_and_drawn_below_follows_the_list(
    tree: dict[str, str],
) -> None:
    page = tree[PAGE]
    home = re.search(r'<svg class="dag" data-home="([^"]+)"', page)
    assert home is not None
    marked = [
        unescape(re.search(r'data-view="([^"]+)"', attrs).group(1))  # type: ignore[union-attr]
        for _s, attrs, _b in rows(page)
        if 'aria-selected="true"' in attrs
    ]
    assert marked == [unescape(home.group(1))]
    assert (
        page.index('id="sets-list"')
        < page.index('class="drawn-below"')
        < page.index('class="figure-cap"')
    )


def test_retire_is_in_a_row_only_with_a_service(
    pages: dict[str, str],  # noqa: F811
    static_pages: dict[str, str],  # noqa: F811
) -> None:
    assert any('class="retire-act"' in body for _s, _a, body in rows(pages[PAGE]))
    assert not any("retire-act" in body for _s, _a, body in rows(static_pages[PAGE]))
    assert rows(static_pages[PAGE])


def test_a_folded_route_has_a_layout_with_every_fold_open(folded: dict[str, str]) -> None:
    page = folded[PAGE]
    lays = layouts_of(page)
    with_folds = [k for k, lay in lays.items() if any(n.startswith("fold:") for n in lay["nodes"])]
    routes_folded = sorted({k.split("~")[0] for k in with_folds})
    assert routes_folded
    for key in routes_folded:
        whole = lays.get(f"{key}~open")
        assert whole is not None, (key, sorted(lays))
        assert not any(n.startswith("fold:") for n in whole["nodes"])
    assert re.search(
        r'<p class="figure-folds" hidden>Proved statements folded · '
        r'<button type="button" class="unfold-all"[^>]*>unfold</button></p>',
        page,
    ), "the figure's heading says so"


# -- in a browser ---------------------------------------------------------------------------------


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def _serve(found: dict[str, str], out: Path) -> Iterator[str]:
    render.write(found, out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


@pytest.fixture(scope="module")
def site_url(tree: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    yield from _serve(tree, tmp_path_factory.mktemp("f34-route-list-site"))


@pytest.fixture(scope="module")
def folded_url(folded: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    yield from _serve(folded, tmp_path_factory.mktemp("f34-route-list-folded"))


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


STATE = """() => ({
  view: document.querySelector('svg.dag').dataset.view,
  rows: [...document.querySelectorAll('li.route-row')].map(r => ({
    view: r.dataset.view, on: r.getAttribute('aria-selected'), hidden: r.hidden,
    visible: r.checkVisibility()})),
  below: document.querySelector('.drawn-below').textContent,
  folds: (document.querySelector('.figure-folds') || {hidden: true}).hidden,
  foldBoxes: [...document.querySelectorAll('svg.dag g.node.fold')]
    .filter(g => !g.classList.contains('off-view')).length,
})"""


def test_a_row_draws_its_route_and_no_row_hides(site_url: str, browser: Any) -> None:
    pg = browser.new_page(viewport={"width": 1440, "height": 1000})
    pg.goto(site_url)
    pg.wait_for_timeout(500)
    pg.locator(".route-tabs button[aria-controls=sets-list]").click()
    start = pg.evaluate(STATE)
    assert all(r["visible"] for r in start["rows"]), start
    other = next(r for r in start["rows"] if r["on"] != "true")
    pg.locator(f'li.route-row[data-view="{other["view"]}"] button.route-n').click()
    pg.wait_for_timeout(1200)
    after = pg.evaluate(STATE)
    assert after["view"] == other["view"]
    assert [r["on"] for r in after["rows"] if r["view"] == other["view"]] == ["true"]
    assert sum(1 for r in after["rows"] if r["on"] == "true") == 1
    assert all(r["visible"] and not r["hidden"] for r in after["rows"]), after
    assert after["below"].startswith("Drawn below ↓ Route ")
    pg.close()


def test_unfold_in_the_figures_heading_opens_every_fold(folded_url: str, browser: Any) -> None:
    pg = browser.new_page(viewport={"width": 1440, "height": 1000})
    pg.goto(folded_url)
    pg.wait_for_timeout(500)
    # the route with a fold: draw it from its row
    lays = pg.evaluate("JSON.parse(document.getElementById('graph-layouts').textContent)")
    key = next(k for k in lays if k.endswith("~open")).removesuffix("~open")
    pg.locator(".route-tabs button[aria-controls=sets-list]").click()
    pg.locator(f'li.route-row[data-view="{key}"] a.route-draw').click()
    pg.wait_for_timeout(1200)
    state = pg.evaluate(STATE)
    assert state["view"] == key and state["folds"] is False and state["foldBoxes"] >= 1, state
    pg.locator("button.unfold-all").click()
    pg.wait_for_timeout(1200)
    opened = pg.evaluate(STATE)
    assert opened["view"] == f"{key}~open" and opened["foldBoxes"] == 0, opened
    assert pg.locator("button.unfold-all").inner_text() == "fold"
    pg.locator("button.unfold-all").click()
    pg.wait_for_timeout(1200)
    assert pg.evaluate(STATE)["view"] == key
    pg.close()


def test_a_routes_name_says_a_statements_name_never_its_id() -> None:
    from opn_site import one_view  # noqa: PLC0415

    rows = {"t--h4--h1": {"label": "the window statement"}, "t--h4": {}, "t": {}}
    name_of = lambda n: str(rows[n].get("label") or n)  # noqa: E731
    said = one_view.named_ids("Iterate t--h4--h1 from t--h4; then stop", rows, name_of)
    assert said == "Iterate the window statement from t--h4; then stop"


def test_the_pickers_box_does_not_widen_a_phone(site_url: str, browser: Any) -> None:
    """Found on the live erdos-257 render while building this (2026-11-27): with "Drawn below"
    moved out of the picker's box the box no longer wrapped, and its one line of help ran to
    568px on a 390px phone."""
    pg = browser.new_page(viewport={"width": 390, "height": 900})
    pg.goto(site_url)
    pg.wait_for_timeout(500)
    wide = pg.evaluate("document.documentElement.scrollWidth")
    tap = pg.evaluate("document.querySelector('.sel-tap').getBoundingClientRect().right")
    pg.close()
    assert wide <= 390 and tap <= 390, (wide, tap)


def test_two_routes_never_share_a_name() -> None:
    """Live erdos-1094, 2026-11-27: Routes 1 and 3 both read "Baker, Harman and Pintz (2001)…",
    because a route was named by its last choice alone and they differ in an earlier one. A name
    another route has is told apart by the choice above it."""
    from test_routes_view import node  # noqa: PLC0415

    from opn_site import one_view  # noqa: PLC0415

    doc = {
        "schema": "graph/v12",
        "target_id": "t",
        "root": "t",
        "nodes": [
            node("t", origin="authored", routes=[["t--a", "t--b"]]),
            node("t--a", routes=[["t--a--x"], ["t--a--y"]], approaches=["first way", "second way"]),
            node("t--b", routes=[["t--b--u"], ["t--b--v"]], approaches=["by sieve", "by descent"]),
            node("t--a--x"),
            node("t--a--y"),
            node("t--b--u"),
            node("t--b--v"),
        ],
    }
    picture = one_view.drawing(doc, [], href={}, prefix="t")
    names = re.findall(r'<span class="route-name">([^<]+)</span>', picture.table)
    assert len(names) == 4 and len(set(names)) == 4, names
    assert sum("sieve" in n for n in names) == 2 and sum("First way" in n for n in names) == 2
