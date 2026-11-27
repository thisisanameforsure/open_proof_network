"""F34-T39 (REMINDERS-erdos-257 item 22; handoff §3.4.6 layout B, mockups ``New-Phone-Select``,
``New-Phone-Every-Tab``): on a phone a statement's record opens directly under it in the outline,
with its dark header, its tabs and their counts, and both buttons; the outline continues below.
That holds from the start — the problem's own statement, selected when the page opens, has its
record under its row, not after the whole drawing — and after a tap closes a record again.

Run with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest \\
    site/tests/test_f34_phone_panel_under.py``
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

WHERE = """() => {
  const panel = [...document.querySelectorAll('.panel[data-node]')].find(p => !p.hidden);
  const li = panel.parentNode.closest('ol.route-outline > li');
  const after = li ? [...li.parentNode.children].slice([...li.parentNode.children].indexOf(li) + 1)
    .filter(x => !x.hidden).length : null;
  return {node: panel.dataset.node, under: li ? li.dataset.node : null, rowsAfter: after,
          head: !!panel.querySelector('.panel-head'), tabs: !!panel.querySelector('.panel-tabs'),
          buttons: panel.querySelectorAll('.panel-always a, .panel-always .btn').length};
}"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    tmp = tmp_path_factory.mktemp("f34-phone-under")
    out = tmp / "site"
    render.write(render_tree(two_routes(tmp / "g")), out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


def test_on_a_phone_a_tapped_statements_record_is_under_it(site_url: str) -> None:
    """F34-T51 (ROUND-2 D8) restates T39's "from the start": REMINDERS item 22 asks that
    *tapping* a statement open its record under it, and the problem's own record open as the
    page loaded buried the outline under it. Now no record is open until a row is tapped
    (``test_f34_phone_head_once``); a tapped row's record is under it with the dark header, the
    tabs and both buttons, the outline continuing below; its header closes it."""
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 390, "height": 900})
        pg.goto(site_url)
        pg.wait_for_timeout(400)
        open_at_start = pg.evaluate(
            "[...document.querySelectorAll('.panel[data-node]')]"
            ".filter(p => !p.hidden && p.checkVisibility()).length"
        )
        first = pg.locator("ol.route-outline > li:not([hidden]) > a[data-node]").nth(0)
        first_id = first.get_attribute("data-node")
        first.click()
        pg.wait_for_timeout(400)
        tapped: dict[str, Any] = pg.evaluate(WHERE)
        pg.locator("ol.route-outline > li.selected .panel-head").click()
        pg.wait_for_timeout(400)
        closed = pg.evaluate(
            "[...document.querySelectorAll('.panel[data-node]')]"
            ".filter(p => !p.hidden && p.checkVisibility()).length"
        )
        b.close()
    assert open_at_start == 0
    assert tapped["node"] == first_id and tapped["under"] == first_id, tapped
    assert tapped["head"] and tapped["tabs"] and tapped["buttons"] >= 2, tapped
    assert tapped["rowsAfter"] and tapped["rowsAfter"] > 0, "the outline continues below"
    assert closed == 0


def test_on_a_wide_screen_the_record_stays_beside_the_drawing(site_url: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(site_url)
        pg.wait_for_timeout(400)
        m: dict[str, Any] = pg.evaluate(WHERE)
        b.close()
    assert m["under"] is None, m


def test_the_selected_rows_chip_keeps_its_own_look() -> None:
    """The selected row's dark link style is for the statement's link; the "+ n speculative"
    link beside it keeps its own quiet look (found in the capture of erdos-257 at 390)."""
    import re  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    css = (Path(__file__).resolve().parents[1] / "opn_site/static/site.css").read_text()
    rule = re.search(r"\.route-outline > li\.selected > a\.spec-more \{([^}]*)\}", css)
    assert rule is not None and "background: none" in rule.group(1)
    assert css.index(rule.group(0)) > css.index(".route-outline > li.selected > a {")
