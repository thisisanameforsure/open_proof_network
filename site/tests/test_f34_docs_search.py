"""F34-T10 (Q13; handoff §3.3): Docs search — a JSON index of every Docs page's headings and text,
written at build, and a same-origin script over it; the sidebar is the fallback without it.

Static: ``/docs/search.json`` holds one entry per Docs page (its address, title, group, each
heading with its anchor, and its text as a reader sees it); every Docs page carries the search
box hidden and ``/docs.js``. In a browser: typing finds the pages that hold every word, best
first, linking a matching heading's anchor; a query that matches nothing says so; with the
script off the box stays hidden and the sidebar is the way round.
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

import fixture
import pytest
from test_f34_docs import GUIDE

from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.org"


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build(tmp_path_factory.mktemp("f34-docs-search"))
    (root / "AGENTS.md").write_text(GUIDE, encoding="utf-8")
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO, api_url=API)


def docs_paths(pages: dict[str, str]) -> list[str]:
    return sorted(
        p for p in pages if p == "docs/index.html" or re.fullmatch(r"docs/[a-z-]+/index\.html", p)
    )


def test_the_index_has_one_entry_per_docs_page(pages: dict[str, str]) -> None:
    index = json.loads(pages["docs/search.json"])
    hrefs = sorted(e["href"] for e in index["pages"])
    want = sorted("/" + p.removesuffix("index.html") for p in docs_paths(pages))
    assert hrefs == want
    for e in index["pages"]:
        assert e["title"] and e["group"] and e["text"], e["href"]
        page = pages[e["href"].lstrip("/") + "index.html"]
        for h in e["headings"]:
            assert f'id="{h["id"]}"' in page, (e["href"], h)
        # what a reader sees, not markup: no attribute survives ("0 < k" and "<id>" are prose)
        assert "class=" not in e["text"] and "href=" not in e["text"], e["href"]


def test_every_docs_page_carries_the_hidden_box_and_the_script(pages: dict[str, str]) -> None:
    for p in docs_paths(pages):
        page = pages[p]
        assert re.search(r'<div class="docs-search" role="search"[^>]*hidden>', page), p
        assert '<script src="/docs.js"></script>' in page, p
    assert "/docs.js" in render.SCRIPTS


# -- in a browser ---------------------------------------------------------------------------


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def served(pages: dict[str, str], tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    out: Path = tmp_path_factory.mktemp("f34-docs-search-site")
    render.write(pages, out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}"
        srv.shutdown()


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def results(page: Any) -> list[str]:
    return list(
        page.evaluate(
            "() => [...document.querySelectorAll('.docs-results a')]"
            ".map(a => a.getAttribute('href'))"
        )
    )


def test_typing_finds_the_pages_that_hold_every_word(served: str, browser: Any) -> None:
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(served + "/docs/", wait_until="load")
    box = page.locator('.docs-search input[type="search"]')
    box.wait_for()
    box.fill("token")
    page.wait_for_function("() => document.querySelectorAll('.docs-results a').length > 0")
    found = results(page)
    assert any(h.startswith("/docs/token/") for h in found), found
    assert found[0].startswith("/docs/token/"), "the page titled by the word comes first"
    box.fill("zzqqxx nothing")
    page.wait_for_selector(".docs-results .cue")
    assert results(page) == []
    assert "No page" in page.inner_text(".docs-results")
    page.close()


def test_without_the_script_the_box_stays_hidden(served: str, browser: Any) -> None:
    ctx = browser.new_context(java_script_enabled=False)
    page = ctx.new_page()
    page.goto(served + "/docs/token/", wait_until="load")
    assert not page.is_visible(".docs-search")
    assert page.is_visible("nav.docs-side")
    ctx.close()
