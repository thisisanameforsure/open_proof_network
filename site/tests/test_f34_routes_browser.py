"""F34-T12 (R14): the route drawing in a browser.

The page opens on its home route (the proving set with the fewest open statements) without
writing a hash; Esc and pressing the shown set again come back to it; Tree and List switch
between the selector and the sets table in the same place.

Run with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest \\
    site/tests/test_f34_routes_browser.py``
"""

from __future__ import annotations

import functools
import http.server
import socketserver
import threading
from collections.abc import Iterator
from typing import Any

import pytest
from harness import TARGET
from test_routes_view import render_tree, two_routes

from opn_site import render

sync_api = pytest.importorskip("playwright.sync_api")
Browser = Any


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    tmp = tmp_path_factory.mktemp("f34-routes-browser")
    out = tmp / "site"
    render.write(render_tree(two_routes(tmp / "g")), out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(site_url: str, browser: Browser) -> Iterator[Any]:
    """One page per test, closed after it: a page left open in front would leave the next one
    in a background tab, where Chromium throttles the animation frames a transition needs."""
    pg = browser.new_page(viewport={"width": 1280, "height": 900})
    pg.goto(site_url, wait_until="load")
    pg.wait_for_timeout(700)  # the opening transition
    yield pg
    pg.close()


def settles_on(page: Any, key: str) -> None:
    """Wait for the drawing to come to rest on a view: ``data-view`` is written when a
    transition ends (600ms by design, longer on a busy machine), so a fixed wait races it."""
    page.wait_for_function(
        "k => document.querySelector('svg.dag:not(.band)').getAttribute('data-view') === k",
        arg=key,
        timeout=5000,
    )


def view(page: Any) -> tuple[str, str]:
    return (
        page.get_attribute("svg.dag:not(.band)", "data-view"),
        page.get_attribute("svg.dag:not(.band)", "data-home"),
    )


def test_the_page_opens_on_its_home_route_and_writes_no_hash(page: Any) -> None:
    shown, home = view(page)
    assert home and shown == home
    assert page.evaluate("location.hash") == ""
    pressed = page.get_attribute(f'svg.selector [data-view="{home}"]', "aria-pressed")
    assert pressed == "true"


def test_escape_and_a_second_press_come_back_home(page: Any) -> None:
    _shown, home = view(page)
    other = page.evaluate(
        """home => [...document.querySelectorAll('svg.selector [data-view^="sel/"]')]
                 .map(e => e.getAttribute('data-view')).find(v => v !== home)""",
        home,
    )
    assert other
    page.click(f'svg.selector [data-view="{other}"]')
    settles_on(page, other)
    assert "view=" in page.evaluate("location.hash")
    page.keyboard.press("Escape")
    settles_on(page, home)
    assert "view=" not in page.evaluate("location.hash")  # home is the default: not written
    page.click(f'svg.selector [data-view="{other}"]')
    settles_on(page, other)
    page.click(f'svg.selector [data-view="{other}"]')
    settles_on(page, home)


def test_tree_and_list_switch_in_place(page: Any) -> None:
    assert page.is_visible(".route-tabs")
    assert page.is_visible("#sets-tree") and not page.is_visible("#sets-list")
    page.click('.route-tabs [aria-controls="sets-list"]')
    assert page.is_visible("#sets-list") and not page.is_visible("#sets-tree")
    assert page.get_attribute('.route-tabs [aria-controls="sets-list"]', "aria-selected") == "true"
    # The table sits where the tree was: right after it in the drawing's card.
    same_card = page.evaluate(
        "document.getElementById('sets-list').parentNode === "
        "document.getElementById('sets-tree').parentNode"
    )
    assert same_card
    page.click('.route-tabs [aria-controls="sets-tree"]')
    assert page.is_visible("#sets-tree") and not page.is_visible("#sets-list")


def test_without_the_script_both_views_stay(site_url: str, browser: Browser) -> None:
    ctx = browser.new_context(java_script_enabled=False)
    page = ctx.new_page()
    page.goto(site_url, wait_until="load")
    assert not page.is_visible(".route-tabs")
    assert page.is_visible("#sets-tree") and page.is_visible("#sets-list")
    ctx.close()
