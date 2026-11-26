"""F34-T19 (handoff §3.5): the review page leads with what it asks.

* A heading that says what the review is: "Does the Lean say <the problem>?", the problem named
  by the head of its title (before any colon), or by its id; the formal "Formalization review of
  <id>" stays as the kicker.
* One line on who does what, before anything else.
* The questions first, as section 1; questions of the same kind in a row grouped under one
  heading ("Questions 2 to 7: constant changes", with an en dash).
* Candidates, pairs, tests and screens after them, each folded; signatures open, since the sign
  form is there. Each section keeps its id, so every old link still lands.
"""

from __future__ import annotations

import re

import pytest
from harness import TARGET
from test_review_page import PAGE, SECTIONS, page, pages, root, site  # noqa: F401

from opn_site import model, render


def test_the_heading_asks_the_question(page: str, site: model.Site) -> None:  # noqa: F811
    tv = site.targets[TARGET]
    title = str((tv.record or {}).get("title") or "")
    named = title.split(":", 1)[0].strip() if title else TARGET
    h1 = re.search(r"<h1>(.*?)</h1>", page, re.S)
    assert h1 is not None
    assert re.sub(r"<[^>]+>", "", h1.group(1)) == f"Does the Lean say {named}?"
    assert f"Formalization review of {TARGET}" in re.sub(r"<[^>]+>", "", page)
    assert '<p class="review-who">' in page
    assert page.index('<p class="review-who">') < page.index('id="questions"')


def test_questions_come_first_and_the_exhibits_are_folded(page: str) -> None:  # noqa: F811
    order = ["questions", "candidates", "pairs", "tests", "screens", "signatures"]
    starts = [page.index(f'id="{sid}"') for sid in order]
    assert starts == sorted(starts), order
    assert set(order) == set(SECTIONS)
    for sid in ("candidates", "pairs", "tests", "screens"):
        assert re.search(rf'<details class="review-fold"><summary><h2 id="{sid}">', page), sid
    for sid in ("questions", "signatures"):
        assert re.search(rf'<h2 id="{sid}">', page), sid
        assert not re.search(rf'<summary><h2 id="{sid}">', page), sid


@pytest.mark.parametrize(
    ("kinds", "groups"),
    [
        ([], []),
        (["constant"], [(1, 1, "constant")]),
        (
            ["other", "constant", "constant", "constant", "connective", "constant"],
            [(1, 1, "other"), (2, 4, "constant"), (5, 5, "connective"), (6, 6, "constant")],
        ),
    ],
)
def test_questions_of_one_kind_in_a_row_are_one_group(
    kinds: list[str], groups: list[tuple[int, int, str]]
) -> None:
    assert render.question_groups(kinds) == groups


def test_a_group_of_several_is_headed_by_its_range_and_kind() -> None:
    want = "Questions 2\N{EN DASH}7: constant changes"
    assert render.question_group_head(2, 7, "constant") == want
    assert render.question_group_head(3, 3, "constant") == ""


def test_the_words_math_is_marked_for_the_renderer() -> None:
    """Handoff §3.5: the raw TeX in the review's words renders — marked ``.math`` as the problem
    page marks it, with the renderer loaded on the page."""
    words = render.math("Let $A\\subseteq\\mathbb{N}$ be infinite.")
    assert '<span class="math">' in words
