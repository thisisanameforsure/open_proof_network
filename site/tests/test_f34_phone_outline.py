"""F34-T17 (R17; handoff §3.4.6): at phone width the selected route is an outline.

Static: the page carries the routes as an outline — every statement on a route once, top to
bottom from the problem, indented by its depth, each a link to its own page — beside the drawing.

At 390px: the drawing gives way to the outline, which shows only the selected route's
statements; every row is at least 44px tall and nothing scrolls sideways; tapping a statement
opens its record directly under it, and tapping it again closes it.
"""

from __future__ import annotations

import functools
import http.server
import re
import socketserver
import threading
from collections.abc import Iterator
from typing import Any

import pytest
from harness import TARGET
from test_one_view_markup import layouts_in
from test_products import ROOT_NODE
from test_routes_view import THIRD, render_tree, two_routes

from opn_site import render

PAGE = f"problems/{TARGET}/index.html"


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    return render_tree(two_routes(tmp_path_factory.mktemp("f34-outline") / "g"))


def rows(page: str) -> list[tuple[str, int]]:
    outline = re.search(r'<ol class="route-outline"[^>]*>(.*?)</ol>', page, re.S)
    assert outline is not None
    return [
        (m.group(2), int(m.group(1)))
        for m in re.finditer(r'<li class="depth-(\d+)" data-node="([^"]+)">', outline.group(1))
    ]


def test_every_route_statement_once_from_the_problem_down(pages: dict[str, str]) -> None:
    page = pages[PAGE]
    found = rows(page)
    ids = [n for n, _d in found]
    assert len(ids) == len(set(ids))
    on_route = {n for n in layouts_in(page)["routes"]["nodes"] if "@" not in n}
    assert set(ids) == on_route
    assert found[0] == (ROOT_NODE, 0)
    assert all(d >= 1 for n, d in found[1:]), found
    for nid in ids:
        assert f'href="/nodes/{TARGET}/{nid}/"' in page


# -- at phone width ----------------------------------------------------------------------------


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def served(pages: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    out = tmp_path_factory.mktemp("f34-outline-site")
    render.write(pages, out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def phone(served: str, browser: Any) -> Iterator[Any]:
    pg = browser.new_page(viewport={"width": 390, "height": 844})
    pg.emulate_media(reduced_motion="reduce")
    pg.goto(served, wait_until="load")
    yield pg
    pg.close()


def shown_rows(page: Any) -> list[str]:
    return list(
        page.evaluate(
            "[...document.querySelectorAll('.route-outline > li')]"
            ".filter(li => li.checkVisibility()).map(li => li.dataset.node)"
        )
    )


def test_the_outline_replaces_the_drawing_and_follows_the_route(phone: Any) -> None:
    assert not phone.is_visible(".dag-scroll") and phone.is_visible(".route-outline")
    home = phone.get_attribute("svg.dag:not(.band)", "data-home")
    view_nodes = phone.evaluate(
        "k => Object.keys("
        "JSON.parse(document.getElementById('graph-layouts').textContent)[k].nodes)",
        home,
    )
    assert set(shown_rows(phone)) == {n for n in view_nodes if "@" not in n}
    heights = phone.evaluate(
        "[...document.querySelectorAll('.route-outline > li > a')]"
        ".filter(a => a.checkVisibility()).map(a => a.getBoundingClientRect().height)"
    )
    assert heights and min(heights) >= 44, heights
    assert phone.evaluate("document.documentElement.scrollWidth") <= 390


def test_tapping_a_statement_opens_its_record_under_it(phone: Any) -> None:
    item = phone.locator(f'.route-outline > li[data-node="{THIRD}"] > a')
    item.click()
    row = f'.route-outline > li[data-node="{THIRD}"]'
    panel = phone.locator(f'{row} > .panel[data-node="{THIRD}"]')
    panel.wait_for(state="visible")
    assert phone.evaluate("document.documentElement.scrollWidth") <= 390
    # F34-T51 (ROUND-2 D8): the record's dark header stands in the row's place and closes it
    panel.locator(".panel-head").click()
    phone.wait_for_selector(f'.panel[data-node="{THIRD}"]', state="hidden")
    assert phone.locator(f'.route-outline > li[data-node="{THIRD}"] > .panel').count() == 0
