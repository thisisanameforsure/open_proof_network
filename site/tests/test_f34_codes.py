"""F34-T4 (R6, handoff §6): internal codes out of reader-facing prose; two copy defects.

* R6 is held page by page (F34-Q18): a page joins ``CLEAN`` when the task that rebuilds it takes
  its decision numbers, attestation numbers and motion ids out of the visible text. A code may still
  sit in a hover card or the footer's "Source of this page".
* A motion that passed with no counted vote passed at once (the panel's only member opened it, or a
  curator opened an invitation), and says so, instead of "passed, 0 yes · 0 no" (erdos-257's #1).
* The pages that offer "Sign in with GitHub" say that contributing needs no account.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

import fixture
import pytest

from opn_site import model, render

REPO = "https://github.com/example/graph"
API = "https://api.example.org"
CODE = re.compile(r"\bD-\d+\b|\battestation \d{3,}|\bmotion:\d+|\bF\d\d-[TRQ]\d+")
#: Pages whose visible text carries no code. Each rebuild task of F34 adds its page here.
CLEAN = ("rules/index.html", "about/index.html", "problems/index.html")  # T5: Problems


class _Visible(HTMLParser):
    VOID = frozenset({"br", "img", "input", "meta", "link", "hr", "wbr", "path", "circle", "rect"})
    HIDDEN = ("term-card", "page-source")

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[bool] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.VOID:
            return
        cls = dict(attrs).get("class") or ""
        hidden = tag in ("code", "pre", "script", "style", "title") or any(
            h in cls for h in self.HIDDEN
        )
        self.stack.append(hidden)

    def handle_endtag(self, tag: str) -> None:
        if tag not in self.VOID and self.stack:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if not any(self.stack):
            self.text.append(data)


def visible_codes(html: str) -> list[str]:
    p = _Visible()
    p.feed(html)
    return CODE.findall(" ".join(p.text))


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build_with_stewards(tmp_path_factory.mktemp("f34-codes"))
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO, api_url=API)


@pytest.mark.parametrize("rel", CLEAN)
def test_clean_pages_show_no_internal_codes(pages: dict[str, str], rel: str) -> None:
    assert visible_codes(pages[rel]) == []


def test_a_motion_passed_without_a_vote_says_so(tmp_path_factory: pytest.TempPathFactory) -> None:
    root = fixture.build(tmp_path_factory.mktemp("f34-motion"))
    r = render.Renderer(model.load_site(root, fixture.COMMIT), repo_url=REPO)
    motion = {
        "n": 1,
        "kind": "invite",
        "subject": {"login": "riversupport"},
        "opened_by": "thisisanameforsure",
        "opened": "2026-10-28",
        "closes": "2026-11-11",
        "state": "passed",
        "yes": 0,
        "no": 0,
    }
    line = r.motion_line(motion, [])
    assert "0 yes" not in line and "0 no" not in line
    assert "passed at once, without a vote" in line
    voted = r.motion_line({**motion, "yes": 2, "no": 1}, [])
    assert "passed</span>, 2 yes · 1 no" in voted


def test_the_sign_in_pages_say_contributing_needs_no_account(pages: dict[str, str]) -> None:
    steward_pages = [rel for rel, html in pages.items() if 'class="steward-form"' in html]
    assert steward_pages, "guard: the fixture has a problem open to a steward"
    for rel in [*steward_pages, "me/index.html"]:
        html = pages[rel]
        assert 'class="anon-note"' in html, rel
        note = html[html.index('class="anon-note"') :]
        note = note[: note.index("</p>")]
        assert "no account" in note and render.GUIDE_HREF in note, rel


def test_a_steward_invited_by_the_panel_says_so_in_words() -> None:
    """F34-T5 found it on the live Problems page: "admitted by motion:1" (erdos-257's co-steward).
    The panel's motion is the record's id for the act; the reader is told who acted."""
    words = render.Renderer.admitted(None, {"login": "riversupport", "admitted_by": "motion:1"})  # type: ignore[arg-type]
    assert "invited by the panel" in words
    assert visible_codes(words) == []
    assert 'data-motion="1"' in words  # the record's id stays on the element
