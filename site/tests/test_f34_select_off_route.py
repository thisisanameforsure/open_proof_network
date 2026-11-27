"""F34-T36 (REMINDERS-erdos-257 item 16; handoff §3.4.3: "every box in the route tree, and every
statement in §2, is selectable"): a statement in "Not on a route" — its line in a group's list, or
its box in the group's small tree — selects into the same panel as a statement of the drawing,
and the panel comes into view; the page does not navigate. With no script the same links lead to
the statement's own page.

Run with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest \\
    site/tests/test_f34_select_off_route.py``
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
from test_crux_band import CRUX, band_tree
from test_one_view import VARIANT, off_route
from test_routes_view import render_tree

from opn_site import render

STATE = """(id) => ({
  shown: [...document.querySelectorAll('.panel[data-node]')].filter(p => !p.hidden)
    .map(p => p.dataset.node),
  path: location.pathname,
  inView: (r => r.top < innerHeight && r.bottom > 0)(
    document.querySelector('.panel[data-node="' + id + '"]').getBoundingClientRect()),
})"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def list_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    """F34-T43: a group drawn as a tree has no list, so the list line is a group with none —
    "Proposed for no statement" in the off-route fixture."""
    tmp = tmp_path_factory.mktemp("f34-select-off-list")
    out = tmp / "site"
    render.write(render_tree(off_route(tmp / "g")), out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    tmp = tmp_path_factory.mktemp("f34-select-off")
    out = tmp / "site"
    render.write(render_tree(band_tree(tmp / "g")), out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


def _click(site_url: str, selector: str, width: int, nid: str = CRUX) -> dict[str, Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": width, "height": 900})
        pg.goto(site_url)
        pg.wait_for_timeout(300)
        el = pg.locator(selector).first
        el.scroll_into_view_if_needed()
        el.click()
        pg.wait_for_timeout(400)
        out: dict[str, Any] = pg.evaluate(STATE, nid)
        b.close()
    return out


@pytest.mark.parametrize("width", [1440, 390])
def test_a_listed_statement_selects_into_the_panel(list_url: str, width: int) -> None:
    got = _click(list_url, f'section.off-route li[data-node="{VARIANT}"] > a', width, VARIANT)
    assert got["shown"] == [VARIANT], got
    assert got["path"] == f"/problems/{TARGET}/", got
    assert got["inView"], got


def test_a_box_in_a_small_tree_selects_into_the_panel(site_url: str) -> None:
    got = _click(site_url, f'section.off-route svg.mini-tree g.node[data-node="{CRUX}"]', 1440)
    assert got["shown"] == [CRUX], got
    assert got["path"] == f"/problems/{TARGET}/", got
    assert got["inView"], got
