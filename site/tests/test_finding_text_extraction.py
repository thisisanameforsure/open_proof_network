"""F04-T41: the problem page's text, extracted, keeps its words apart.

A reader who copies the page, a screen reader in browse mode, or an agent that strips the tags
reads what the markup holds, not what the stylesheet shows. Two places ran words together:

(a) a glossary term writes its label and then its hidden definition card with nothing between
    them, so the status tag read ``openListed, and its statements accept work`` and a card's
    protocol line ran on from its meaning (``…acceptedprotocol: D-9``);
(b) a statement-graph pill writes its label, its outline badge's count and its ``<title>`` with
    no whitespace, so a pill read ``h2--h11erdos-1094--h2--h1`` (its test is in
    ``test_finding_dag_labels.py``).

On screen both are right; the fix must keep them so (the evidence is a screenshot pair).
"""

from __future__ import annotations

from html.parser import HTMLParser

import fixture
import pytest

from opn_site import model, render

REPO = "https://github.com/example/graph"
PAGE = "problems/propositional/index.html"
MARK = "\x00"  # where a card, or a block inside one, begins or ends in the extracted text
CARD_BLOCKS = {"term-card", "proto", "why"}


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build(tmp_path_factory.mktemp("extract"))
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


class _Extract(HTMLParser):
    """The page's text as a tag-stripper sees it, with ``MARK`` where each card block opens."""

    def __init__(self) -> None:
        super().__init__()
        self.out: list[str] = []
        self.skip = 0
        self.spans: list[bool] = []  # open spans: whether each is a card block

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.skip += 1
        if tag == "span":
            block = bool(set((dict(attrs).get("class") or "").split()) & CARD_BLOCKS)
            self.spans.append(block)
            if block:
                self.out.append(MARK)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.skip -= 1
        if tag == "span" and self.spans and self.spans.pop():
            self.out.append(MARK)

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.out.append(data)


def extracted(html: str) -> str:
    p = _Extract()
    p.feed(html)
    p.close()
    return "".join(p.out)


def joins(text: str) -> list[str]:
    """Each place a card block meets the text beside it with neither side a space."""
    bad = []
    for i, ch in enumerate(text):
        if ch != MARK:
            continue
        before = text[:i].rstrip(MARK)[-1:] or " "
        after = text[i + 1 :].lstrip(MARK)[:1] or " "
        if not before.isspace() and not after.isspace():
            bad.append(text[max(0, i - 30) : i + 30].replace(MARK, "|"))
    return bad


def test_every_term_card_is_set_apart_from_its_label(pages: dict[str, str]) -> None:
    """(a): each ``.term`` on the problem page, its card, the card's protocol and reason lines,
    and whatever follows the card are separated by whitespace in the stripped text."""
    html = pages[PAGE]
    assert html.count('class="term-card"') >= 8, "guard: the fixture page carries its terms"
    text = extracted(html)
    assert joins(text) == []
