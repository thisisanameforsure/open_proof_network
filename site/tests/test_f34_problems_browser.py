"""F34-T5 (R7, AC8): the Problems page's filters in a browser.

Each control filters the rows already in the HTML and writes its URL parameter; a reload restores
the view; the old ``?filter=`` links still apply; the waiting table shows fifty rows and a "Show
50 more" button. The paging test serves a copy of the page with 120 waiting rows, since the
fixture has one.

Run with Playwright (not part of ``make verify``):
``uv run --frozen --with 'playwright==1.58.0' python -m pytest \\
    site/tests/test_f34_problems_browser.py``
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

import fixture
import pytest
from harness import TARGET
from test_f34_problems import entry, write_ledger

from opn_site import model, render

sync_api = pytest.importorskip("playwright.sync_api")
Browser = Any

REPO = "https://github.com/example/graph"
MANY = 120


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


def _many_waiting(page: str) -> str:
    """The page with its one waiting row copied ``MANY`` times, each with its own id."""
    row = re.search(r'<tr data-id="[^"]+"[^>]*>.*?</tr>', page, re.S)
    assert row is not None
    copies = "".join(
        row.group(0).replace(f'data-id="{fixture.STEWARDLESS_TARGET}"', f'data-id="w-{i:03}"')
        for i in range(MANY)
    )
    return page.replace(row.group(0), copies, 1)


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    tmp = tmp_path_factory.mktemp("f34-problems-browser")
    root = fixture.build_with_stewards(tmp / "g")
    write_ledger(root, "alice", [entry(TARGET, "and-reassoc", "2026-09-10T12:00:00Z")])
    out = tmp / "site"
    render.write(render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO), out)
    page = (out / "problems" / "index.html").read_text(encoding="utf-8")
    (out / "many").mkdir()
    (out / "many" / "index.html").write_text(_many_waiting(page), encoding="utf-8")
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


def shown(page: Any) -> list[str]:
    return list(
        page.evaluate(
            """() => [...document.querySelectorAll('[data-id]')]
                 .filter(r => !r.hidden).map(r => r.getAttribute('data-id'))"""
        )
    )


def open_page(browser: Browser, url: str) -> Any:
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(url, wait_until="load")
    return page


def test_the_controls_appear_with_the_script(site_url: str, browser: Browser) -> None:
    page = open_page(browser, site_url + "/problems/")
    assert page.locator(".filters").is_visible() and page.locator(".chips").is_visible()
    every = shown(page)
    assert TARGET in every and fixture.STEWARDLESS_TARGET in every
    page.close()


def test_search_filters_and_writes_the_url(site_url: str, browser: Browser) -> None:
    page = open_page(browser, site_url + "/problems/")
    page.fill('[name="q"]', "stewardless")
    assert shown(page) == [fixture.STEWARDLESS_TARGET]
    assert "q=stewardless" in page.url
    page.reload(wait_until="load")
    assert page.input_value('[name="q"]') == "stewardless"
    assert shown(page) == [fixture.STEWARDLESS_TARGET]
    page.close()


def test_status_steward_and_area_filter(site_url: str, browser: Browser) -> None:
    page = open_page(browser, site_url + "/problems/")
    page.select_option('[name="status"]', "worked")
    assert shown(page) == [TARGET] and "status=worked" in page.url
    page.select_option('[name="status"]', "")
    page.select_option('[name="steward"]', "needs")
    needs = shown(page)
    assert fixture.STEWARDLESS_TARGET in needs and fixture.STEWARDED_TARGET not in needs
    page.select_option('[name="steward"]', "")
    page.click('button[data-area="other"]')
    assert all(
        page.get_attribute(f'[data-id="{tid}"]', "data-area") == "other" for tid in shown(page)
    )
    assert "area=other" in page.url
    page.close()


def test_sort_by_name_reorders_the_rows(site_url: str, browser: Browser) -> None:
    page = open_page(browser, site_url + "/problems/?sort=name")
    worked = page.evaluate(
        """() => [...document.querySelectorAll('[data-section=worked] [data-id]')]
                 .filter(r => !r.hidden).map(r => r.getAttribute('data-id'))"""
    )
    assert worked == sorted(worked) and len(worked) >= 2
    page.close()


@pytest.mark.parametrize(
    ("old", "check"),
    [
        ("filter=unstewarded", lambda r: r == "needs"),
        ("filter=proved", None),
        ("filter=open", None),
    ],
)
def test_old_filter_links_still_apply(
    site_url: str, browser: Browser, old: str, check: Any
) -> None:
    page = open_page(browser, f"{site_url}/problems/?{old}")
    ids = shown(page)
    if old == "filter=unstewarded":
        assert ids and all(
            page.get_attribute(f'[data-id="{t}"]', "data-steward") == "needs" for t in ids
        )
    elif old == "filter=proved":
        assert all(page.get_attribute(f'[data-id="{t}"]', "data-stage") == "proved" for t in ids)
    else:
        assert ids and all(
            int(page.get_attribute(f'[data-id="{t}"]', "data-open")) > 0 for t in ids
        )
    page.close()


def test_the_waiting_table_pages_fifty_at_a_time(site_url: str, browser: Browser) -> None:
    page = open_page(browser, site_url + "/many/")
    waiting = """() => [...document.querySelectorAll('[data-section=waiting] [data-id]')]
                      .filter(r => !r.hidden).length"""
    assert page.evaluate(waiting) == 50
    assert page.inner_text("[data-showing]") == f"Showing 50 of {MANY}"
    page.click("[data-more]")
    assert page.evaluate(waiting) == 100
    page.click("[data-more]")
    assert page.evaluate(waiting) == MANY
    assert page.locator("[data-more]").is_hidden()
    page.close()


def test_without_the_script_every_row_shows(tmp_path: Path) -> None:
    """R7: the whole list is in the HTML, and nothing in it starts hidden but the controls."""
    root = fixture.build_with_stewards(tmp_path)
    page = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)[
        "problems/index.html"
    ]
    assert not re.search(r"<(?:article|tr)\b[^>]*data-id=[^>]*\bhidden\b", page)
