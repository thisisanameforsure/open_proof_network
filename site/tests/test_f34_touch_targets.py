"""F34-T40 (REMINDERS-erdos-257 item 23; handoff §3.4.6): on a phone every touch target is at least
44px, and the site switches to its phone layout at one width, the same in the stylesheet and in
graph.js.

The route selector's numbered ends and splits are the one exception the geometry forces: they sit
26px apart, so each carries an invisible hit square filling its column (26px at the selector's own
size) rather than 44px targets that would cover their neighbours; a square, so a fork still holds
no circle (F30-T10).

The browser half runs with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest \\
    site/tests/test_f34_touch_targets.py``
"""

from __future__ import annotations

import functools
import http.server
import re
import socketserver
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET
from test_crux_band import band_tree
from test_routes_view import render_tree, two_routes

from opn_site import one_view, render

STATIC = Path(__file__).resolve().parents[1] / "opn_site" / "static"
PHONE = 760


def test_the_phone_layout_switches_at_one_width() -> None:
    css = (STATIC / "site.css").read_text(encoding="utf-8")
    js = (STATIC / "graph.js").read_text(encoding="utf-8")
    narrow = {int(w) for w in re.findall(r"@media \(max-width: (\d+)px\)", css) if int(w) < 800}
    scripted = {int(w) for w in re.findall(r'matchMedia\("\(max-width: (\d+)px\)"\)', js)}
    assert narrow == {PHONE} and scripted == {PHONE}, (narrow, scripted)


def test_every_selector_mark_has_a_hit_square_filling_its_column(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path / "g"))[f"problems/{TARGET}/index.html"]
    nodes = re.findall(r'<g class="sel-node [^"]*"[^>]*>(.*?)</g>', page, re.S)
    assert nodes
    for body in nodes:
        h, w = one_view.SEL_COL // 2, one_view.SEL_COL
        assert f'<rect class="hit" x="-{h}" y="-{h}" width="{w}" height="{w}"/>' in body, body


TARGETS = """() => {
  const sel = 'main button, main [role=tab], main summary, main ol.route-outline > li > a,'
    + ' main .btn, main a.act, main a.spec-more';
  const small = [];
  for (const el of document.querySelectorAll(sel)) {
    if (el.closest('[hidden]') || el.closest('svg')) continue;
    if (getComputedStyle(el).display === 'none') continue;
    const r = el.getBoundingClientRect();
    const name = el.tagName + '.' + el.className;
    if (r.width && r.height < 44) small.push([name, Math.round(r.height)]);
  }
  const hit = document.querySelector('svg.selector .hit');
  return {small, hitFill: hit ? getComputedStyle(hit).fill : null,
          hitEvents: hit ? getComputedStyle(hit).pointerEvents : null};
}"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    tmp = tmp_path_factory.mktemp("f34-touch")
    out = tmp / "site"
    render.write(render_tree(band_tree(tmp / "g")), out)  # folds, a speculative chip, a selector
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


def test_on_a_phone_every_control_is_at_least_44px(site_url: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 390, "height": 900})
        pg.goto(site_url)
        pg.wait_for_timeout(400)
        m: dict[str, Any] = pg.evaluate(TARGETS)
        b.close()
    assert m["small"] == [], m["small"]
    assert m["hitFill"] not in (None, "none") and m["hitEvents"] != "none", m
