"""F34-T42 (REMINDERS-erdos-257 item 10, second half; handoff §3.4.2; mockup
``New-Erdos257-Route1``): "A statement used as a lemma from elsewhere shows as a dashed
'uses: gap lemma' box beside its user." On erdos-257 the route's representation statement uses
the gap lemma, which no route of it draws, and the drawing said nothing of it.

Each pill whose statement uses others (graph.json's ``uses``, the merged proof's use lines) carries
a dashed chip per used statement, "uses: <its label>", inside the pill's own group so it moves
with it; a click on the chip selects the used statement into the panel.

The browser half runs with Playwright (not part of ``make verify``).
"""

from __future__ import annotations

import functools
import http.server
import re
import socketserver
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from harness import TARGET
from test_crux_band import CRUX, band_tree
from test_routes_view import THIRD, render_tree, two_routes

from opn_site import render

PAGE = f"problems/{TARGET}/index.html"


def pill(page: str, nid: str) -> str:
    m = re.search(
        rf'<g class="node[^"]*" data-node="{re.escape(nid)}"[^>]*>(.*?)</g></a>', page, re.S
    )
    assert m is not None, nid
    return m.group(1)


def test_a_statement_that_uses_another_says_so_on_its_pill(tmp_path: Path) -> None:
    page = render_tree(band_tree(tmp_path / "g"))[PAGE]
    chips = re.findall(
        r'<g class="uses-chip" data-uses="([^"]+)"[^>]*>.*?<text[^>]*>([^<]+)</text>',
        pill(page, THIRD),
        re.S,
    )
    assert [c[0] for c in chips] == [CRUX], chips
    assert chips[0][1].startswith("uses: "), chips


def test_no_use_no_chip(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path / "g"))[PAGE]
    assert 'class="uses-chip"' not in page


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    tmp = tmp_path_factory.mktemp("f34-uses")
    out = tmp / "site"
    render.write(render_tree(band_tree(tmp / "g")), out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


def test_a_click_on_the_chip_selects_the_used_statement(site_url: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(site_url + "#view=all")
        pg.wait_for_timeout(700)
        chip = pg.locator(f'svg.dag g.uses-chip[data-uses="{CRUX}"]').first
        chip.scroll_into_view_if_needed()
        chip.click()
        pg.wait_for_timeout(500)
        shown = pg.evaluate(
            "[...document.querySelectorAll('.panel[data-node]')].filter(p => !p.hidden)"
            ".map(p => p.dataset.node)"
        )
        path = pg.evaluate("location.pathname")
        b.close()
    assert shown == [CRUX] and path == f"/problems/{TARGET}/", (shown, path)
