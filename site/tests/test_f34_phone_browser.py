"""F34-T3 (R5): no page scrolls sideways at 390px, and the Rules table is one table at any width.

Measured on the live graph before the fix (``engineering/evidence/F34/task-3.txt``): Problems was
759px wide on a 390px screen because a row's grid column (``1fr``, whose minimum is its content)
could not shrink below a display formula; Contributors was 548px because its ledger tables sat in no
scrolling box; and at 1440 the Rules table was laid out as a grid, header row on the left and rows
on the right, because the About page's ``.rules`` grid class matched it too.

Run with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest \
    site/tests/test_f34_phone_browser.py``
"""

from __future__ import annotations

import functools
import http.server
import shutil
import socketserver
import threading
from collections.abc import Iterator
from typing import Any

import fixture
import pytest
import yaml

from opn_gate import products
from opn_site import model, render

sync_api = pytest.importorskip("playwright.sync_api")
Browser = Any  # playwright is not a dependency of the type check (``--with`` at run time)

REPO = "https://github.com/example/graph"
TARGET = "wide-display"
ROOT = "wide-display-root"
#: A display formula with no break in it, wider than a phone (the erdos-883 shape).
WIDE = (
    "$$G(A) = \\left\\{ (a, b) \\in A \\times A : a \\neq b,\\ "
    "\\gcd(a, b) > 1,\\ a + b \\equiv 0 \\pmod{4},\\ \\text{and } a b \\le n^2 \\right\\}$$"
)
PAGES = (
    "/",
    "/problems/",
    "/contributors/",
    "/docs/",
    "/about/",
    "/rules/",
    f"/problems/{TARGET}/",
    "/problems/propositional/",
)


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    from harness import take_in  # noqa: PLC0415

    tmp = tmp_path_factory.mktemp("f34-phone")
    root = fixture.build(tmp / "g")
    staged = tmp / ROOT
    shutil.copytree(fixture.nodes_dir(root) / "and-reassoc", staged)
    meta = yaml.safe_load((staged / "META.yaml").read_text())
    meta["id"] = ROOT
    (staged / "META.yaml").write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    (staged / "Proof.lean").unlink(missing_ok=True)
    take_in(
        root,
        target_id=TARGET,
        root_dir=staged,
        title="A problem whose statement is one wide formula",
        track="open",
        informal=None,
        paraphrase=f"For every finite set $A$, {WIDE}",
        sources=[fixture.UNLICENSED],
        qa_summary=fixture.QA_SUMMARY,
        domains=["number-theory"],
    )
    products.generate(root, rendered_from=fixture.COMMIT, commit_time=fixture.NOW).write(root)
    out = tmp / "site"
    render.write(render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO), out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}"
        srv.shutdown()


@pytest.fixture(scope="module")
def browser() -> Iterator[Browser]:
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.mark.parametrize("path", PAGES)
def test_no_page_scrolls_sideways_at_390(site_url: str, browser: Browser, path: str) -> None:
    page = browser.new_page(viewport={"width": 390, "height": 900})
    page.goto(site_url + path, wait_until="load")
    page.wait_for_timeout(300)  # KaTeX typesets after load
    width = page.evaluate("document.documentElement.scrollWidth")
    page.close()
    assert width <= 390, f"{path} is {width}px wide at 390"


def test_the_wide_formula_scrolls_inside_its_own_box(site_url: str, browser: Browser) -> None:
    """Guard: the fixture's formula really is wider than a phone, so the page test above bites."""
    page = browser.new_page(viewport={"width": 390, "height": 900})
    page.goto(f"{site_url}/problems/{TARGET}/", wait_until="load")
    page.wait_for_timeout(300)
    box = page.evaluate(
        """() => { const d = document.querySelector('.katex-display');
                   return d ? {scroll: d.scrollWidth, client: d.clientWidth,
                                ox: getComputedStyle(d).overflowX} : null; }"""
    )
    page.close()
    assert box is not None, "the formula was not typeset as display math"
    assert box["scroll"] > box["client"], box
    assert box["ox"] in ("auto", "scroll"), box


@pytest.mark.parametrize("path", PAGES)
def test_every_table_fits_or_scrolls_in_its_own_box(
    site_url: str, browser: Browser, path: str
) -> None:
    page = browser.new_page(viewport={"width": 390, "height": 900})
    page.goto(site_url + path, wait_until="load")
    loose = page.evaluate(
        """() => [...document.querySelectorAll('main table')].filter(t => {
             for (let e = t; e && e !== document.body; e = e.parentElement) {
               if (/(auto|scroll)/.test(getComputedStyle(e).overflowX)) return false; }
             return t.getBoundingClientRect().right > document.documentElement.clientWidth + 1;
           }).map(t => t.className)"""
    )
    page.close()
    assert loose == [], f"{path}: tables past the screen with no scroll box: {loose}"


def test_the_rules_table_is_one_table_at_1440(site_url: str, browser: Browser) -> None:
    """One table, head over rows; each value on one line ("14 days", not "da ys"), and the Set
    column's "the default (never changed)" in at most two lines (the review saw five)."""
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(site_url + "/rules/", wait_until="load")
    shape = page.evaluate(
        """() => { const t = document.querySelector('table.rules');
                   const head = t.querySelector('thead tr').getBoundingClientRect();
                   const row = t.querySelector('tbody tr').getBoundingClientRect();
                   const lines = (td) => { const r = document.createRange();
                     r.selectNodeContents(td);
                     return new Set([...r.getClientRects()].map(x => Math.round(x.top))).size; };
                   const col = (n) =>
                     [...t.querySelectorAll(`tbody td:nth-child(${n})`)].map(lines);
                   return {display: getComputedStyle(t).display, headLeft: head.left,
                           rowLeft: row.left, headWidth: head.width, rowWidth: row.width,
                           valueLines: col(2), setLines: col(4)}; }"""
    )
    page.close()
    assert shape["display"] == "table", shape
    assert abs(shape["headLeft"] - shape["rowLeft"]) < 1, shape
    assert abs(shape["headWidth"] - shape["rowWidth"]) < 1, shape
    assert shape["valueLines"] and max(shape["valueLines"]) == 1, shape
    assert max(shape["setLines"]) <= 2, shape
