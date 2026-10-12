"""F04-T43: the catalog's reasons are labelled as score points.

On the live erdos-1094 page the evidence listed ``+2 attempted by AlphaProof Nexus (Feb 2026)``
a few lines above ``Documented external attempts counting toward D-9's M: 1``. The ``+2`` is the
catalog's score points for that reason (F14-R10), not a count of attempts, but nothing on the
page said so, and a reader saw two attempt counts that disagree. The reasons now sit under a
heading naming the score they make up and saying their numbers are points.
"""

from __future__ import annotations

import re

import pytest
from fixture import COMMIT, LISTED_TARGET, build_with_evidenced_target

from opn_site import model, render

REPO = "https://github.com/example/graph"
TARGET_PAGE = f"problems/{LISTED_TARGET}/index.html"


@pytest.fixture(scope="module")
def page(tmp_path_factory: pytest.TempPathFactory) -> str:
    root = build_with_evidenced_target(tmp_path_factory.mktemp("points"))
    return render.render_site(model.load_site(root, COMMIT), repo_url=REPO)[TARGET_PAGE]


def test_the_reasons_are_headed_as_the_scores_points(page: str) -> None:
    start = page.index('<div class="evidence">')
    ul = page.index('<ul class="reasons">', start)
    assert "+2 attempted by AlphaProof Nexus (Feb 2026)" in page[ul:], "guard: the reason is listed"
    # what a reader meets between the evidence's opening line and the list
    head = re.sub(r"<[^>]+>", " ", page[page.index("</p>", start) : ul])
    head = " ".join(head.split())
    assert "Catalog score 6" in head, head
    assert "score points" in head and "not" in head and "attempts" in head, head
