"""F34-T27 (handoff §3.4.2): "A statement that has speculative statements proposed for it carries
'+ 4 speculative ↓', linking to its group in §2."

With the speculative column gone from §1 (Q26), nothing in the drawing said that a statement had
proposals waiting beside it. Each "Proposed for X" group in §2 carries an anchor, and X's pill in
the drawing carries a chip counting the group's statements and naming that anchor. A pill with
no group carries none. The chip sits inside the pill's own group element, so it moves with the
pill through every transition; a click on it scrolls to the group without changing the view.

The browser half runs with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest \\
    site/tests/test_f34_speculative_chips.py``
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
from test_crux_band import CRUX, band_tree
from test_products import ROOT_NODE
from test_routes_view import render_tree, two_routes

from opn_site import render

PAGE = f"problems/{TARGET}/index.html"


def pill(page: str, nid: str) -> str:
    """The markup of ``nid``'s pill in the drawing, from its opening tag to its link's end."""
    m = re.search(
        rf'<g class="node[^"]*" data-node="{re.escape(nid)}"[^>]*>(.*?)</g></a>', page, re.S
    )
    assert m is not None, nid
    return m.group(1)


def test_a_statement_with_proposals_carries_a_chip_naming_its_group(tmp_path: Path) -> None:
    page = render_tree(band_tree(tmp_path / "g"))[PAGE]
    group = re.search(
        r'<div class="off-group" id="([^"]+)"><h3>Proposed for .*?<ul>(.*?)</ul>', page, re.S
    )
    assert group is not None, "the group carries an anchor"
    anchor, items = group.group(1), group.group(2)
    n = items.count("<li ")
    assert f'data-node="{CRUX}"' in items
    chip = re.search(
        r'<g class="spec-chip" data-to="([^"]+)"[^>]*>.*?<text[^>]*>([^<]+)</text>',
        pill(page, ROOT_NODE),
        re.S,
    )
    assert chip is not None, "the root's pill carries the chip"
    assert chip.group(1) == anchor
    assert chip.group(2) == f"+ {n} speculative ↓"
    assert page.count('class="spec-chip"') == 1, "only the statement with proposals"


def test_no_proposals_no_chip(tmp_path: Path) -> None:
    page = render_tree(two_routes(tmp_path / "g"))[PAGE]
    assert 'class="spec-chip"' not in page


# -- in a browser ---------------------------------------------------------------------------------


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    tmp = tmp_path_factory.mktemp("f34-spec-chips")
    out = tmp / "site"
    render.write(render_tree(band_tree(tmp / "g")), out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


def test_a_click_on_the_chip_scrolls_to_the_group_and_keeps_the_view(site_url: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg: Any = b.new_page(viewport={"width": 1280, "height": 900})
        pg.goto(site_url)
        before = pg.evaluate(
            "() => [location.hash, document.querySelector('svg.dag').dataset.view, scrollY]"
        )
        pg.locator("g.spec-chip").first.click()
        pg.wait_for_timeout(700)
        after = pg.evaluate(
            "() => [location.hash, document.querySelector('svg.dag').dataset.view, scrollY,"
            " (r => r.top)(document.querySelector('.off-group').getBoundingClientRect())]"
        )
        b.close()
    assert after[0] == before[0] and after[1] == before[1], (before, after)
    assert after[2] > before[2], "the page scrolled"
    assert 0 <= after[3] < 300, "the group is in view"


def test_the_phone_outline_carries_the_same_link(tmp_path: Path) -> None:
    """A phone shows the outline in place of the drawing (T17); the statement's row carries the
    same words, linking to the group, as the phone mockup draws it."""
    page = render_tree(band_tree(tmp_path / "g"))[PAGE]
    outline = re.search(r'<ol class="route-outline"[^>]*>(.*?)</ol>', page, re.S)
    assert outline is not None
    row = re.search(rf'<li [^>]*data-node="{ROOT_NODE}"[^>]*>(.*?)</li>', outline.group(1), re.S)
    assert row is not None
    anchor = re.search(r'<div class="off-group" id="([^"]+)">', page)
    assert anchor is not None
    more = re.search(r'<a class="spec-more" href="#([^"]+)">([^<]+)</a>', row.group(1))
    assert more is not None and more.group(1) == anchor.group(1)
    assert more.group(2) == re.search(
        r'<g class="spec-chip"[^>]*>.*?<text[^>]*>([^<]+)</text>', page, re.S
    ).group(1)  # type: ignore[union-attr]
