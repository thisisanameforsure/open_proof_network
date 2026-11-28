"""F34-T24 (R15; handoff §3.4.2, §3.4.6), the outline's half: proved statements folded for every
reader, each fold a visible box naming how many proved statements it holds, which opens in place.

A fold is a run of sibling statements whose subtrees are entirely proved, holding at least two
statements (one proved statement is shown, not boxed). Without the script every row shows.
"""

from __future__ import annotations

import functools
import http.server
import json
import re
import socketserver
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from harness import TARGET
from test_decompositions import HOLE_IDS
from test_products import attest as gate_attest
from test_products import nodes_dir
from test_routes_view import render_tree, two_routes

from opn_site import render

PAGE = f"problems/{TARGET}/index.html"


def proved_pair(root: Path) -> Path:
    """``two_routes`` with both holes of the first split proved: that route has nothing open."""
    for n, hole in enumerate(HOLE_IDS, start=20):
        d = nodes_dir(root) / hole
        (d / "Proof.lean").write_text(
            (d / "Statement.lean").read_text(encoding="utf-8").replace("sorry", "trivial"),
            encoding="utf-8",
        )
        gate_attest(root, hole, n=n, footprint={"nodes": []})
    return root


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    return render_tree(proved_pair(two_routes(tmp_path_factory.mktemp("f34-folds") / "g")))


def test_the_outline_lists_the_proved_pair_as_rows(pages: dict[str, str]) -> None:
    """F34-T56 restates T24's check of the outline's markup: the page carries every statement
    of the routes as a row and no fold of its own (the rule over every route together counted
    statements the drawn route does not hold); graph.js boxes the rows the drawing folds."""
    page = pages[PAGE]
    outline = re.search(r'<ol class="route-outline".*?</ol>', page, re.S)
    assert outline is not None
    rows = re.findall(r'<li class="depth-\d+" data-node="([^"]+)">', outline.group(0))
    assert set(HOLE_IDS) <= set(rows)
    assert "fold" not in outline.group(0)


# -- in a browser ------------------------------------------------------------------------------


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def served(pages: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    out = tmp_path_factory.mktemp("f34-folds-site")
    render.write(pages, out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def shown(page: Any) -> list[str]:
    return list(
        page.evaluate(
            "[...document.querySelectorAll('.route-outline > li[data-node]')]"
            ".filter(li => li.checkVisibility()).map(li => li.dataset.node)"
        )
    )


def test_the_fold_is_a_box_that_opens_in_place(served: str, browser: Any) -> None:
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.emulate_media(reduced_motion="reduce")
    page.goto(served, wait_until="load")
    box = page.locator(".route-outline .fold-box")
    box.wait_for(state="visible")
    assert "2 proved statements" in box.inner_text()
    assert not set(HOLE_IDS) & set(shown(page))
    box.click()
    assert set(HOLE_IDS) <= set(shown(page))
    assert box.get_attribute("aria-expanded") == "true"
    box.click()
    assert not set(HOLE_IDS) & set(shown(page))
    page.close()


def test_without_the_script_every_row_shows(served: str, browser: Any) -> None:
    ctx = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
    page = ctx.new_page()
    page.goto(served, wait_until="load")
    assert set(HOLE_IDS) <= set(shown(page))
    assert not page.is_visible(".route-outline .fold-box")
    ctx.close()


# -- the drawing's folds (the owner, 2026-11-26: a box, the tree laid out again round it) ------


def layouts_of(page: str) -> dict[str, Any]:
    m = re.search(r'<script type="application/json" id="graph-layouts">(.*?)</script>', page, re.S)
    assert m is not None
    return dict(json.loads(m.group(1).replace("<\\/", "</")))


def test_the_route_is_laid_out_folded_and_each_fold_has_an_open_layout(
    pages: dict[str, str],
) -> None:
    page = pages[PAGE]
    lays = layouts_of(page)
    home = re.search(r'<svg class="dag" data-home="([^"]+)"', page)
    assert home is not None
    key = home.group(1)
    folded = set(lays[key]["nodes"])
    fold_ids = [n for n in folded if n.startswith("fold:")]
    assert len(fold_ids) == 1 and not set(HOLE_IDS) & folded
    opened = set(lays[f"{key}~fold0"]["nodes"])
    assert set(HOLE_IDS) <= opened and not any(n.startswith("fold:") for n in opened)
    mark = re.search(
        rf'<g class="node fold[^"]*" data-node="{re.escape(fold_ids[0])}" '
        rf'data-open="{re.escape(key)}~fold0"[^>]*>.*?</g>',
        page,
        re.S,
    )
    assert mark is not None and "2 proved statements" in mark.group(0)


def test_clicking_the_box_lays_the_tree_out_again_with_the_fold_open(
    served: str, browser: Any
) -> None:
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.emulate_media(reduced_motion="reduce")
    page.goto(served, wait_until="load")
    home = page.get_attribute("svg.dag:not(.band)", "data-home")
    assert page.get_attribute("svg.dag:not(.band)", "data-view") == home
    box = page.locator("svg.dag:not(.band) g.node.fold:not(.off-view)")
    assert box.count() == 1
    hole = f'svg.dag:not(.band) g.node[data-node="{HOLE_IDS[0]}"]'
    assert "off-view" in (page.get_attribute(hole, "class") or "")
    box.click()
    page.wait_for_function(
        "k => document.querySelector('svg.dag:not(.band)').getAttribute('data-view') === k",
        arg=f"{home}~fold0",
    )
    assert "off-view" not in (page.get_attribute(hole, "class") or "")
    pressed = page.get_attribute(f'svg.selector [data-view="{home}"]', "aria-pressed")
    assert pressed == "true", "an open fold is still its route in the selector"
    page.mouse.move(5, 5)
    page.keyboard.press("Escape")
    page.wait_for_function(
        "k => document.querySelector('svg.dag:not(.band)').getAttribute('data-view') === k",
        arg=home,
    )
    page.close()
