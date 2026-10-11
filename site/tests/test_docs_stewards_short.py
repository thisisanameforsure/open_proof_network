"""F23-T10: the Docs page's Stewards section fits on one screen and points at the form.

The long account moved to what the form needs (D-32 v3.33): a reader who wants to steward a
problem clicks once to /steward/ instead of reading a page first. Measured in a browser at 1440 by
the evidence run (engineering/evidence/F23/task-10.txt); here, its words are bounded and the link
is there.
"""

from __future__ import annotations

import re

import fixture
import pytest

from opn_site import model, render

REPO = "https://github.com/example/graph"
#: About what fits beside the header at 1440 in the Docs page's measure.
MAX_WORDS = 220  # was 358; the browser measure is in task-10.txt


@pytest.fixture(scope="module")
def section(tmp_path_factory: pytest.TempPathFactory) -> str:
    root = fixture.build(tmp_path_factory.mktemp("docs-stewards"))
    docs = render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)[
        "docs/index.html"
    ]
    start = docs.index('<h2 id="stewards">')
    return docs[start : docs.index("<h2", start + 1)]


def test_the_section_points_at_the_form(section: str) -> None:
    assert 'href="/steward/"' in section


def test_the_section_is_short(section: str) -> None:
    words = len(re.sub(r"<[^>]+>", " ", section).split())
    assert words <= MAX_WORDS, words
