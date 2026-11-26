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
