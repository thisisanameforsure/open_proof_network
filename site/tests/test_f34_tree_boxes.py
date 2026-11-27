"""F34-T32 (REMINDERS-erdos-257 item 11; mockup ``New-Erdos257``, ``-Unfolded``,
``New-Select-Side``): the tree's boxes as the mockup draws them — read from the browser's computed
styles, since a stylesheet's text says little about which rule wins.

Every box is white with a grey hairline and a 12.5px sans label, not underlined mono; a proved
statement is told by its blue dot, not a grey-filled pill; an open one by an ink ring; the
selected box is filled ink with its label in white, and the lines of its path from the problem
are drawn heavier.

Run with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest site/tests/test_f34_tree_boxes.py``
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
from test_crux_band import band_tree
from test_routes_view import render_tree

from opn_site import render

WHITE = "rgb(255, 255, 255)"
PROVED = "rgb(42, 77, 143)"  # --proved, #2a4d8f
INK = "rgb(27, 27, 26)"  # --ink, #1b1b1a

STYLES = """() => {
  const cs = (el) => getComputedStyle(el);
  const pill = (g) => ({
    id: g.dataset.node,
    rectFill: cs(g.querySelector('rect.pill')).fill,
    rectStroke: cs(g.querySelector('rect.pill')).stroke,
    rectWidth: cs(g.querySelector('rect.pill')).strokeWidth,
    dotFill: cs(g.querySelector('circle:not(.halo)')).fill,
    dotStroke: cs(g.querySelector('circle:not(.halo)')).stroke,
    textFill: cs(g.querySelector('text')).fill,
    family: cs(g.querySelector('text')).fontFamily,
    size: cs(g.querySelector('text')).fontSize,
    underline: cs(g.parentNode).textDecorationLine,
  });
  // §2's small trees have their own look (F34-T43): dotted boxes, serif labels
  const all = [...document.querySelectorAll(
    'svg.dag:not(.mini-tree) g.node:not(.fold):not(.off-view)')];
  return {
    proved: all.filter(g => g.classList.contains('proved')).map(pill),
    open: all.filter(g => !g.classList.contains('proved')
      && !g.classList.contains('status-superseded')).map(pill),
    selected: all.filter(g => g.classList.contains('selected')).map(pill),
  };
}"""


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def styles(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict[str, Any]]:
    sync_api = pytest.importorskip("playwright.sync_api")
    tmp = tmp_path_factory.mktemp("f34-boxes")
    out = tmp / "site"
    render.write(render_tree(band_tree(tmp / "g")), out)  # it draws proved and open
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        with sync_api.sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1440, "height": 900})
            pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/")
            pg.wait_for_timeout(500)
            yield pg.evaluate(STYLES)
            b.close()
        srv.shutdown()


def test_every_box_is_white_with_a_sans_label_not_underlined(styles: dict[str, Any]) -> None:
    boxes = styles["proved"] + styles["open"]
    assert boxes
    for b in boxes:
        if b in styles["selected"]:
            continue
        assert b["rectFill"] == WHITE, b
        assert "IBM Plex Sans" in b["family"] and b["size"] == "12.5px", b
        assert b["underline"] == "none", b


def test_proved_is_a_blue_dot_not_a_grey_pill(styles: dict[str, Any]) -> None:
    assert styles["proved"], "the fixture has a proved statement"
    for b in styles["proved"]:
        if b in styles["selected"]:
            continue
        assert b["dotFill"] == PROVED and b["rectFill"] == WHITE, b


def test_open_is_an_ink_ring(styles: dict[str, Any]) -> None:
    assert styles["open"], "the fixture has an open statement"
    for b in styles["open"]:
        if b in styles["selected"]:
            continue
        assert b["dotStroke"] == INK and b["dotFill"] == "none", b


def test_the_selected_box_is_filled_ink(styles: dict[str, Any]) -> None:
    assert len(styles["selected"]) == 1
    b = styles["selected"][0]
    assert b["rectFill"] == INK and b["textFill"] == WHITE, b
