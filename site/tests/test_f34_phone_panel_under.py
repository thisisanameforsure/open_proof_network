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


def test_on_a_phone_the_record_is_under_its_statement_from_the_start(site_url: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 390, "height": 900})
        pg.goto(site_url)
        pg.wait_for_timeout(400)
        start: dict[str, Any] = pg.evaluate(WHERE)
        other = pg.locator("ol.route-outline > li:not([hidden]) > a[data-node]").nth(1)
        other_id = other.get_attribute("data-node")
        other.click()
        pg.wait_for_timeout(400)
        tapped: dict[str, Any] = pg.evaluate(WHERE)
        other.click()  # closes it: the problem's own record, under its own row
        pg.wait_for_timeout(400)
        closed: dict[str, Any] = pg.evaluate(WHERE)
        b.close()
    assert start["under"] == start["node"], start
    assert start["head"] and start["tabs"] and start["buttons"] >= 2, start
    assert start["rowsAfter"] and start["rowsAfter"] > 0, "the outline continues below"
    assert tapped["node"] == other_id and tapped["under"] == other_id, tapped
    assert closed["node"] == start["node"] and closed["under"] == start["node"], closed


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
