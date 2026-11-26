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


def test_figure_one_is_the_top_of_the_tree_with_the_rest_counted() -> None:
    """Home's Figure 1, as the mockup: the drawing cut after its first rows of statements, and
    how many statements the cut leaves out, for the problem's page to show."""
    import json  # noqa: PLC0415

    from opn_site import render  # noqa: PLC0415

    nodes = {
        "r": [100, 10, 80],
        "r@1": [130, 60, 8],
        "a": [20, 110, 60],
        "b": [120, 110, 60],
        "a1": [20, 210, 60],
        "a2": [100, 210, 60],
        "a3": [180, 310, 60],
    }
    doc = json.dumps({"routes": {"w": 300, "h": 360, "nodes": nodes, "lines": []}})
    layouts = f'<script type="application/json" id="graph-layouts">{doc}</script>'
    svg = (
        '<svg class="dag" data-view="routes" viewBox="0 0 300 360" width="300" height="360"></svg>'
    )
    cut, more = render.figure_top(svg, layouts, rows=3)
    assert more == 1  # rows at 10, 110 and 210 are kept; a3 at 310 is cut; a junction is no row
    assert 'viewBox="0 0 300 ' in cut and 'height="360"' not in cut
    whole, none = render.figure_top(svg, layouts, rows=9)
    assert (whole, none) == (svg, 0)


def test_the_problem_page_shows_its_review_as_a_card(pages: dict[str, str]) -> None:  # noqa: F811
    """§3, as the mockup: a card asking whether the Lean says the conjecture, the review's six
    stages, and the way to open the review; none on a problem with no review."""
    from test_review_page import PROBLEM  # noqa: PLC0415

    problem = pages[PROBLEM]
    card = re.search(r'<div class="review-card">(.*?)</ol></div>', problem, re.S)
    assert card is not None
    assert "Does the Lean say the conjecture?" in card.group(1)
    assert 'href="/problems/' in card.group(1) and "/review/" in card.group(1)
    assert '<ol class="review-progress">' in card.group(1)
    assert problem.index('id="statement"') < problem.index('class="review-card"')
    others = [p for rel, p in pages.items() if rel.startswith("problems/") and rel != PROBLEM]
    assert any('class="review-card"' not in p for p in others)
