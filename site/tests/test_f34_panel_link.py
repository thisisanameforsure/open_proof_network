"""F34-T37 (REMINDERS-erdos-257 item 15; handoff §3.4.3 layout A, mockup ``New-Select-Side``): with
the panel beside the drawing, a line runs from the selected box to the panel, and follows the
selection; Esc or selecting the box again returns to the problem's own statement (F34-T16), and the
line with it. With the panel under the statement (a phone), there is no line.

Run with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest site/tests/test_f34_panel_link.py``
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

MEASURE = """() => {
  const link = document.querySelector('svg.panel-link');
  const g = document.querySelector('svg.dag g.node.selected');
  const panel = [...document.querySelectorAll('.panels .panel[data-node]')].find(p => !p.hidden);
  if (!link || getComputedStyle(link).display === 'none' || !g || !panel) {
    return {shown: false, node: g && g.dataset.node};
  }
  const path = link.querySelector('path');
  const n = path.getTotalLength();
  const toPage = (pt) => {
    const m = path.getScreenCTM();
    return {x: m.a * pt.x + m.c * pt.y + m.e, y: m.b * pt.x + m.d * pt.y + m.f};
  };
  const a = toPage(path.getPointAtLength(0)), b = toPage(path.getPointAtLength(n));
  const pill = g.querySelector('rect.pill').getBoundingClientRect();
  const box = panel.getBoundingClientRect();
  return {shown: true, node: g.dataset.node, panel: panel.dataset.node,
          start: [a.x, a.y], end: [b.x, b.y],
          pill: [pill.left, pill.top, pill.right, pill.bottom],
          box: [box.left, box.top, box.right, box.bottom]};
}"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    tmp = tmp_path_factory.mktemp("f34-panel-link")
    out = tmp / "site"
    render.write(render_tree(two_routes(tmp / "g")), out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


def joins(m: dict[str, Any]) -> None:
    """The line starts at the selected box and ends on the panel's left edge."""
    _left, top, right, bottom = m["pill"]
    sx, sy = m["start"]
    assert abs(sx - right) <= 2 and top - 1 <= sy <= bottom + 1, m
    pl, pt, _pr, pb = m["box"]
    ex, ey = m["end"]
    assert abs(ex - pl) <= 2 and pt <= ey <= pb, m


def test_a_line_joins_the_selected_box_to_the_panel_and_follows_it(site_url: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 1000})
        pg.goto(site_url)
        pg.wait_for_timeout(400)
        first = pg.evaluate(MEASURE)
        other = pg.locator("svg.dag g.node:not(.selected):not(.off-view)").first
        other.click()
        pg.wait_for_timeout(700)
        second = pg.evaluate(MEASURE)
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(700)
        back = pg.evaluate(MEASURE)
        b.close()
    assert first["shown"] and first["node"] == first["panel"], first
    joins(first)
    assert second["shown"] and second["node"] != first["node"], second
    assert second["node"] == second["panel"]
    joins(second)
    assert back["shown"] and back["node"] == first["node"], back
    joins(back)


def test_no_line_on_a_phone(site_url: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 390, "height": 900})
        pg.goto(site_url)
        pg.wait_for_timeout(400)
        m = pg.evaluate(MEASURE)
        b.close()
    assert not m["shown"], m
