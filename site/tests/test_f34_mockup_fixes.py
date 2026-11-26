"""F34-T21: differences the side-by-side with the mockups found, each held by a test.

* The review page's "Waiting for the intent signer" warning colour leaked onto the Problems
  page's waiting table, which shares the class name: every statement there showed in rust.
* The review page folds a run of questions of one kind behind its heading (the mockup's
  "Questions 2-7: constant changes ... Show all").
"""

from __future__ import annotations

import re
from pathlib import Path

from test_review_page import page, pages, root, site  # noqa: F401

CSS = Path(__file__).resolve().parents[1] / "opn_site" / "static" / "site.css"


def test_the_warning_colour_is_the_review_lines_alone() -> None:
    css = CSS.read_text(encoding="utf-8")
    rules = re.findall(r"^([^{\n]*)\{[^}]*color: var\(--warn\)", css, re.M)
    bare = [r.strip() for r in rules if re.search(r"(^|[\s,])\.waiting\b", r)]
    assert bare == [], bare
    assert re.search(r"^p\.waiting \{ color: var\(--warn\)", css, re.M)


def test_a_run_of_one_kind_is_never_an_open_heading(page: str) -> None:  # noqa: F811
    """A run's heading is the summary of its fold, not a heading above an open list."""
    assert '<h3 class="question-group">' not in page


def test_the_review_shows_its_six_stages_in_order(page: str) -> None:  # noqa: F811
    """The mockup's progress strip: six stages, each done, now (the first not done) or later."""
    strip = re.search(r'<ol class="review-progress">(.*?)</ol>', page, re.S)
    assert strip is not None
    stages = re.findall(
        r'<li class="rp-(done|now|later)"><span class="rp-n">(\d) · [a-z]+</span>'
        r"<strong>([^<]+)</strong>",
        strip.group(1),
    )
    assert [s[2] for s in stages] == [
        "Candidates", "Pairs", "Answers", "Intent tests", "Screens", "Signatures"
    ]  # fmt: skip
    assert [s[1] for s in stages] == ["1", "2", "3", "4", "5", "6"]
    states = [s[0] for s in stages]
    assert states.count("now") <= 1
    if "now" in states:  # every stage before the one now is done
        assert all(s == "done" for s in states[: states.index("now")]), states
    assert page.index('class="review-progress"') < page.index('id="questions"')
