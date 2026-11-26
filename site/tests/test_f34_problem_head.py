"""F34-T29 (REMINDERS-erdos-257 items 1-3; handoff §3.4.1 item 2, mockup ``New-Erdos257``): the
problem page's head as the mockup draws it.

1. The problem's words are the headline (``h1``); the mono id is no headline but a sidenote. The
   status is a dot and a word beside the stage mark, not a pill; the "statement unchecked" and
   "review: ..." badges become one note: whether the statement is checked, what its review waits
   for, and "Open the review →".
2. The kicker names the problem, then its area: "Erdős problem 257 · number theory".
3. "This problem is open for work" is no line of its own: the steward sentence says it.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

from harness import TARGET
from test_review_page import PROBLEM, page, pages, root, site  # noqa: F401

from opn_site import model, render


def head(html: str) -> str:
    m = re.search(r'<section class="problem-head">(.*?)</section>', html, re.S)
    assert m is not None
    return m.group(1)


def test_the_words_are_the_headline_and_the_id_a_sidenote(pages: dict[str, str]) -> None:  # noqa: F811
    h = head(pages[PROBLEM])
    assert '<h1 class="mono">' not in h
    assert re.search(r'<h1 class="informal-big">.+?</h1>', h, re.S)
    main, notes = h.split('<aside class="margin-notes">', 1)
    assert f'<span class="mono">{TARGET}</span>' in notes
    assert f">{TARGET}<" not in main.split('<p class="crumbs">', 1)[1].split("</p>", 1)[1]


def test_status_is_a_dot_and_a_word_and_the_badges_are_one_note(
    pages: dict[str, str],  # noqa: F811
    site: model.Site,  # noqa: F811
) -> None:
    h = head(pages[PROBLEM])
    assert re.search(r'<span class="status-head"><span class="dot dot-[a-z-]+"></span>', h)
    assert 'class="tag"' not in h and "tag-outline" not in h, "no pill, no badge"
    note = re.search(r'<div class="review-note" role="note">(.*?)</div>', h, re.S)
    assert note is not None
    words = re.sub(r"<[^>]+>", "", note.group(1))
    tv = site.targets[TARGET]
    if str(tv.index_entry.get("fidelity")) == "mechanical-only":
        assert 'The statement is <span class="term" tabindex="0">not yet checked' in note.group(1)
    assert "Its review" in words
    assert f'href="/problems/{TARGET}/review/">Open the review →</a>' in note.group(1)


def test_a_problem_with_no_review_has_no_review_link(tmp_path: Path) -> None:
    from test_routes_view import render_tree, two_routes  # noqa: PLC0415

    text = render_tree(two_routes(tmp_path / "g"))[PROBLEM]
    note = re.search(r'<div class="review-note" role="note">(.*?)</div>', head(text), re.S)
    if note is not None:  # a statement already checked with no review says nothing here
        assert "Open the review" not in note.group(1)


def test_open_for_work_is_in_the_steward_sentence(
    pages: dict[str, str],  # noqa: F811
    site: model.Site,  # noqa: F811
) -> None:
    h = head(pages[PROBLEM])
    assert "This problem is open for work." not in h
    sentence = re.search(r'<p class="head-sentence">(.*?)</p>', h, re.S)
    assert sentence is not None
    tv = site.targets[TARGET]
    if tv.index_entry.get("claimable") and not render.Renderer.is_tutorial(tv):
        assert "Open for work:" in sentence.group(1)


def test_the_kicker_names_the_problem_then_its_area() -> None:
    assert render.problem_name("Erdős problem 257: Let $A$ be infinite.") == "Erdős problem 257"
    assert render.problem_name("Let $A$ be infinite.") is None
    assert render.problem_name("x" * 60 + ": too long to be a name") is None
    tv = SimpleNamespace(
        record={
            "title": "Erdős problem 257: Let $A$ be infinite.",
            "domains": ["number-theory"],
            "provenance": {"upstream_path": "FormalConjectures/ErdosProblems/257.lean"},
        }
    )
    kicker = render.Renderer.problem_kicker(None, tv)  # type: ignore[arg-type]
    assert kicker == "Erdős problem 257 · number theory", kicker
