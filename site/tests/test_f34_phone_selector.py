"""F34-T38 (REMINDERS-erdos-257 item 21; handoff §3.4.6, mockup ``New-Phone-Select``): on a phone
the route selector fits the screen — a wide one is scaled down to the box's width, never clipped
or scrolled sideways — and says under it "Tap a numbered end to draw that route below." On a wide
screen the hint is not shown and the selector keeps its size.

The fixtures' selectors are small enough to fit anyway, so the test widens one to 900px in the
page before measuring: what is checked is that the stylesheet scales a selector to its box.

Run with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest \\
    site/tests/test_f34_phone_selector.py``
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

HINT = "Tap a numbered end to draw that route below."

MEASURE = """() => {
  const sel = document.querySelector('svg.selector');
  sel.setAttribute('width', '900');
  const h = parseFloat(sel.getAttribute('height')), vb = sel.viewBox.baseVal;
  sel.setAttribute('height', String(900 * vb.height / vb.width));
  const wrap = sel.closest('.selector-wrap');
  const s = sel.getBoundingClientRect(), w = wrap.getBoundingClientRect();
  const hint = document.querySelector('.sel-tap');
  return {selRight: s.right, wrapRight: w.right, wrapScroll: wrap.scrollWidth - wrap.clientWidth,
          page: document.documentElement.scrollWidth, h,
          hint: hint ? [getComputedStyle(hint).display !== 'none', hint.textContent.trim()] : null};
}"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    tmp = tmp_path_factory.mktemp("f34-phone-selector")
    out = tmp / "site"
    render.write(render_tree(two_routes(tmp / "g")), out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


def measure(site_url: str, width: int) -> dict[str, Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": width, "height": 900})
        pg.goto(site_url)
        pg.wait_for_timeout(300)
        out: dict[str, Any] = pg.evaluate(MEASURE)
        b.close()
    return out


def test_on_a_phone_a_wide_selector_is_scaled_to_its_box(site_url: str) -> None:
    m = measure(site_url, 390)
    assert m["selRight"] <= m["wrapRight"] + 0.5, m
    assert m["wrapScroll"] <= 0 and m["page"] == 390, m
    assert m["hint"] == [True, HINT], m


def test_on_a_wide_screen_the_hint_is_not_shown(site_url: str) -> None:
    m = measure(site_url, 1440)
    assert m["hint"] is not None and m["hint"][0] is False, m
