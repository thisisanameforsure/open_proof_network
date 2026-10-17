"""F29-T9: a route's approach written as a partial gloss reaches the problem page's selector.

The site reads ``decompositions[].approach`` from ``graph.json`` (F29-R4) and nothing else; this
test runs the generator over a tree holding a merged partial with no comment, no annex and no
declared line, plus a ``gloss/v3`` of kind ``partial`` on it, and reads the gloss's first sentence
in the "Sufficient sets" box where "route 1 of <label>" stood. The sibling route, unglossed,
still falls back to its number, and the partial's record details list the gloss chain without
breaking the page.
"""

from __future__ import annotations

import re
from pathlib import Path

from harness import TARGET
from test_decompositions import PARTIAL
from test_finding_route_gloss import GLOSS_WORDS, partial_doc, put_gloss
from test_routes_view import render_tree, selector_rows, two_routes


def test_the_selector_names_the_glossed_route_by_its_gloss(tmp_path: Path) -> None:
    root = two_routes(tmp_path)
    put_gloss(root, partial_doc(root, module=PARTIAL), GLOSS_WORDS + "\n")
    page = render_tree(root)[f"problems/{TARGET}/index.html"]
    drawing = page[page.index('<svg class="routes-svg"') :]
    drawing = drawing[: drawing.index("</svg>")]
    rows = selector_rows(drawing)
    assert len(rows) == 2, "two routes on the root, two leaves"
    first, second = rows
    assert "Bound the density of the set first." in first
    assert "Then the rest follows" not in first, "the first sentence only"
    assert re.search(r"route 2 of ", second), "the unglossed route falls back to its number"
    assert "route 1 of " not in first


def test_a_partial_gloss_does_not_break_the_record_details(tmp_path: Path) -> None:
    root = two_routes(tmp_path)
    digest, _ = put_gloss(root, partial_doc(root, module=PARTIAL), GLOSS_WORDS + "\n")
    pages = render_tree(root)
    assert any(digest[:12] in page for page in pages.values()), "the version is on some page"
