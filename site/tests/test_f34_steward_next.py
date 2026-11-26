"""F34-T19 (handoff §3.5): the "Become a steward" page says what happens next — five steps in
order, each with its way in: the name goes on the problem, the review's questions, the
literature to confirm, the words to approve, the explainer to sign and the write-up. It is the
onboarding, so it tells a new steward their first jobs. A problem that takes no steward has none.
"""

from __future__ import annotations

import re

import fixture
import pytest

from opn_site import model, render

REPO = "https://github.com/example/graph"


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = fixture.build_with_stewards(tmp_path_factory.mktemp("f34-steward-next"))
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def steps(page: str) -> list[str] | None:
    m = re.search(r'<section class="steward-next">.*?<ol>(.*?)</ol>', page, re.S)
    return re.findall(r"<li>(.*?)</li>", m.group(1), re.S) if m else None


def test_the_five_steps_in_order_each_with_its_way_in(pages: dict[str, str]) -> None:
    page = pages[f"steward/{fixture.STEWARDLESS_TARGET}/index.html"]
    found = steps(page)
    assert found is not None and len(found) == 5, found
    words = ["name", "review", "literature", "approve", "explainer"]
    for item, word in zip(found, words, strict=True):
        assert word in item.lower(), (word, item)
        assert "<a href=" in item, item
    assert f'href="/problems/{fixture.STEWARDLESS_TARGET}/"' in found[0]
    assert 'href="/me/"' in found[3]
    assert 'href="/docs/sign-explainer/"' in found[4]


def test_a_problem_that_takes_no_steward_has_no_next_steps(pages: dict[str, str]) -> None:
    site_pages = [
        p for rel, p in pages.items() if rel.startswith("steward/") and rel.count("/") == 2
    ]
    none = [p for p in site_pages if "This problem takes no steward" in p]
    assert none, "guard: the fixture has a problem that takes no steward"
    assert all(steps(p) is None for p in none)
