"""F34-T16 (R16; handoff §3.4.3): selecting a statement shows its record in five tabs.

Static: every statement's panel carries a tab row (Claim, Proof, Known, Work, Record — only the
parts it has), hidden until the script can switch it, each tab naming the part it shows; a line
naming the statement and its path from the problem; and, always visible, the panel's action and
"Open its page". Without the script every part stays on the page, as before.

In a browser: the problem's own statement is selected on load, on its Claim tab; a tab shows its
part alone (Record opens the record's fold); selecting another statement shows its panel on
Claim and draws its path heavier; Esc comes back to the problem's own statement.
"""

from __future__ import annotations

import functools
import http.server
import re
import socketserver
import threading
from collections.abc import Iterator
from typing import Any

import pytest
from harness import TARGET
from test_products import ROOT_NODE
from test_routes_view import THIRD, render_tree, two_routes

from opn_site import render

PAGE = f"problems/{TARGET}/index.html"
PARTS = ("claim", "how", "known", "work", "record")
NAMES = {"claim": "Claim", "how": "Proof", "known": "Known", "work": "Work", "record": "Record"}


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    return render_tree(two_routes(tmp_path_factory.mktemp("f34-select") / "g"))


def panels(page: str) -> dict[str, str]:
    return {
        m.group(1): m.group(0)
        for m in re.finditer(r'<div class="card panel" data-node="([^"]+)".*?\n</div>', page, re.S)
    }


def test_each_panel_has_its_tabs_hidden_naming_its_parts(pages: dict[str, str]) -> None:
    found = panels(pages[PAGE])
    assert ROOT_NODE in found and THIRD in found
    for nid, panel in found.items():
        tabs = re.search(
            r'<div class="panel-tabs" role="tablist"[^>]*hidden>(.*?)</div>', panel, re.S
        )
        assert tabs is not None, nid
        buttons = re.findall(
            # F34-T35: a tab may carry its count after its name
            r'<button type="button" role="tab" data-tab="([a-z]+)"[^>]*>([^<]+?)'
            r'(?: <span class="tab-n">\d+</span>)?</button>',
            tabs.group(1),
        )
        present = [
            p
            for p in PARTS
            if f'data-section="{p}"' in panel
            or (p == "record" and '<details class="record"' in panel)
        ]
        assert [b[0] for b in buttons] == present, (nid, buttons)
        for part, label in buttons:
            assert label.startswith(NAMES[part]), (nid, part, label)


def test_each_panel_names_its_path_and_keeps_its_ways_out(pages: dict[str, str]) -> None:
    found = panels(pages[PAGE])
    hole = found[THIRD]
    path = re.search(r'<p class="panel-path[^"]*" data-path="([^"]+)"', hole)
    assert path is not None
    ids = path.group(1).split()
    assert ids[0] == ROOT_NODE and ids[-1] == THIRD
    always = re.search(r'<p class="panel-always">.*?</p>', hole, re.S)
    assert always is not None and f'href="/nodes/{TARGET}/{THIRD}/"' in always.group(0)
    root = found[ROOT_NODE]
    assert re.search(r'data-path="' + re.escape(ROOT_NODE) + '"', root)


# -- in a browser ------------------------------------------------------------------------------


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def served(pages: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    out = tmp_path_factory.mktemp("f34-select-site")
    render.write(pages, out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/#view=routes"
        srv.shutdown()


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(served: str, browser: Any) -> Iterator[Any]:
    pg = browser.new_page(viewport={"width": 1440, "height": 900})
    pg.emulate_media(reduced_motion="reduce")
    pg.goto(served, wait_until="load")
    yield pg
    pg.close()


def visible_parts(page: Any, nid: str) -> list[str]:
    return list(
        page.evaluate(
            """nid => [...document.querySelectorAll(
                   `.panel[data-node="${nid}"] .panel-sec[data-section], `
                   + `.panel[data-node="${nid}"] details.record`)]
                 .filter(e => e.checkVisibility()).map(e => e.dataset.section || "record")""",
            nid,
        )
    )


def test_the_problem_opens_on_its_claim_and_a_tab_shows_its_part_alone(page: Any) -> None:
    root = f'.panel[data-node="{ROOT_NODE}"]'
    assert page.is_visible(root) and page.is_visible(f"{root} .panel-tabs")
    assert visible_parts(page, ROOT_NODE) == ["claim"]
    page.click(f'{root} .panel-tabs [data-tab="how"]')
    assert visible_parts(page, ROOT_NODE) == ["how"]
    page.click(f'{root} .panel-tabs [data-tab="record"]')
    assert visible_parts(page, ROOT_NODE) == ["record"]
    assert page.evaluate(f"document.querySelector('{root} details.record').open")
    assert page.is_visible(f"{root} .panel-always")


def test_selecting_another_draws_its_path_and_esc_comes_back(page: Any) -> None:
    page.locator(f'svg.dag g.node[data-node="{THIRD}"]').click()
    hole = f'.panel[data-node="{THIRD}"]'
    page.wait_for_selector(hole, state="visible")
    assert visible_parts(page, THIRD) == ["claim"]
    on_path = page.evaluate(
        "[...document.querySelectorAll('svg.dag path.edge.on-path')].map(e => e.dataset.key)"
    )
    assert on_path and all(THIRD in k or "@" in k for k in on_path), on_path
    page.mouse.move(5, 5)
    page.keyboard.press("Escape")
    page.wait_for_selector(f'.panel[data-node="{ROOT_NODE}"]', state="visible")
    assert not page.is_visible(hole)
    assert page.evaluate("document.querySelectorAll('svg.dag path.edge.on-path').length") == 0


def test_without_the_script_every_part_stays(served: str, browser: Any) -> None:
    ctx = browser.new_context(java_script_enabled=False)
    pg = ctx.new_page()
    pg.goto(served, wait_until="load")
    assert not pg.is_visible(f'.panel[data-node="{ROOT_NODE}"] .panel-tabs')
    assert pg.is_visible(f'.panel[data-node="{ROOT_NODE}"] [data-section="claim"]')
    assert pg.is_visible(f'.panel[data-node="{ROOT_NODE}"] [data-section="how"]')
    ctx.close()
