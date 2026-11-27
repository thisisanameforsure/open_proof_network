"""F34-T52 (ROUND-2 D6): three smaller fixes the owner chose.

1. On a wide screen the selected-statement panel stays in view while a long Figure 1 scrolls
   (live erdos-1094: the right column was empty for about 2000px), and the line from the selected
   box still meets it.
2. The statement is shown once: the headline. The margin note keeps the id and the source; §3
   opens with the review unless the record's wording differs from the headline (a paraphrase's
   note is the one thing that does).
3. Words, not marks, on boxes: the boxed number on a corner said nothing and now says what it
   counts ("2 outlines": the statement's informal outlines, never attempts); the small dotted
   square says the literature status it stands for ("lit: known?", the question mark while it
   awaits a steward's confirmation). Both stay in "Key to the drawing".

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
from types import SimpleNamespace

import pytest
from harness import TARGET
from test_f34_inline_text import TARGET as LISTED
from test_f34_inline_text import pages as listed  # noqa: F401
from test_routes_view import render_tree, two_routes

from opn_site import dag, render

PAGE = f"problems/{TARGET}/index.html"
CSS = (Path(__file__).resolve().parents[1] / "opn_site" / "static" / "site.css").read_text()


# -- 3: words, not marks ---------------------------------------------------------------------------


def text_of(markup: str) -> str:
    m = re.search(r"<text[^>]*>([^<]*)</text>", markup)
    assert m is not None, markup
    return m.group(1)


def test_the_corner_tab_says_what_it_counts() -> None:
    assert text_of(dag.outline_mark(1, 200)) == "1 outline"
    assert text_of(dag.outline_mark(2, 200)) == "2 outlines"
    assert dag.outline_mark(0, 200) == ""
    box = re.search(r'<rect width="(\d+)"', dag.outline_mark(2, 200))
    assert box is not None and int(box.group(1)) >= 50, "wide enough for its words"


def test_the_literature_mark_says_its_status() -> None:
    proposed = dag.literature_mark(dag.LitMark("known", False, "t1009-c"), 200)
    confirmed = dag.literature_mark(dag.LitMark("open", True, "a-steward"), 200)
    assert text_of(proposed) == "lit: known?"
    assert text_of(confirmed) == "lit: open"
    assert 'class="lit-mark lit-known proposed"' in proposed
    assert "awaits confirmation" in proposed, "the full words stay in its title"


def test_both_marks_are_in_the_key() -> None:
    assert "outline" in render.ROUTE_MARK_KEYS or "outline" in render.GLOSSARY_BY_KEY
    assert re.search(r"\.dag \.lit-mark text \{", CSS) and re.search(
        r"\.dag \.outline-mark text \{", CSS
    )


# -- 2: the statement once ------------------------------------------------------------------------


def test_the_statement_is_the_headline_and_nowhere_else(
    listed: dict[str, str],  # noqa: F811
) -> None:
    """A listed problem whose record has a title ("The abc conjecture: …") and a paraphrase."""
    page = listed[f"problems/{LISTED}/index.html"]
    head = re.search(r'<h1 class="informal-big">(.*?)</h1>', page, re.S)
    assert head is not None
    said = re.sub(r"<[^>]+>", "", head.group(1)).strip()
    assert said.startswith("For every"), said
    margin = re.search(r'<aside class="margin-notes">(.*?)</aside>', page, re.S)
    assert margin is not None
    note = re.sub(r"<[^>]+>", "", margin.group(1))
    assert "Id " in note and LISTED in note
    assert "For every" not in note and "finitely many triples" not in note, note
    third = page[page.index('<h2 id="statement">') : page.index('<h2 id="people">')]
    words = re.sub(r"<[^>]+>", "", third)
    assert "finitely many triples" not in words, "§3 does not say the statement again"
    assert "the network's own paraphrase" in words, "what differs from the headline is said"


def test_a_paraphrase_keeps_its_note_in_section_three() -> None:
    words = "Every even number is a sum of two primes."
    r = render.Renderer.__new__(render.Renderer)
    para = SimpleNamespace(record={"paraphrase": words})
    note = r.statement_note(para)  # type: ignore[arg-type]
    assert "the network's own paraphrase" in note and "Every even number" not in note
    own = SimpleNamespace(record={"informal": words})
    assert r.statement_note(own) == ""  # type: ignore[arg-type]


# -- 1: the panel stays in view ------------------------------------------------------------------


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="module")
def site_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    tmp = tmp_path_factory.mktemp("f34-round2-small")
    out = tmp / "site"
    render.write(render_tree(two_routes(tmp / "g")), out)
    handler = functools.partial(_Quiet, directory=str(out))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as srv:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{srv.server_address[1]}/problems/{TARGET}/"
        srv.shutdown()


def test_the_panel_stays_in_view_beside_a_long_figure(site_url: str) -> None:
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1440, "height": 800})
        pg.goto(site_url)
        pg.wait_for_timeout(500)
        # a figure as long as erdos-1094's: 2600px of drawing beside the panel
        pg.evaluate("document.querySelector('.dag-scroll').style.minHeight = '2600px'")
        top = pg.evaluate(
            "document.querySelector('.graph-grid').getBoundingClientRect().top + window.scrollY"
        )
        pg.evaluate("y => window.scrollTo(0, y)", top + 1400)
        pg.wait_for_timeout(400)
        box = pg.evaluate(
            "(() => { const r = document.querySelector('.panel:not([hidden])')"
            ".getBoundingClientRect(); return [r.top, r.bottom]; })()"
        )
        phone = b.new_page(viewport={"width": 390, "height": 800})
        phone.goto(site_url)
        phone.wait_for_timeout(400)
        position = phone.evaluate("getComputedStyle(document.querySelector('.panels')).position")
        b.close()
    assert 0 <= box[0] < 200 and box[1] <= 800, box
    assert position != "sticky", "a phone has one column: nothing to stay beside"
