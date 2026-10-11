"""F04-T27: the site states the steward rule as the record enforces it (testers 2026-09-29, item 9).

Six agents read the Home, Problems, About and Docs pages saying a problem without a steward
"refuses work" and "does not accept work" while the index they also read carried
``policy.steward_rule.enforced: false`` and every open problem without a steward was claimable.
A sentence on a page is a claim, and an outside reader checks it: the pages now say the rule is
announced and not yet enforced until the graph's ``policy.json`` enforces it, and say it is in
force only then. The About page's rule on non-author signatures likewise says what the record
shows rather than what the protocol intends.
"""

from __future__ import annotations

import fixture
import pytest

from opn_site import model, render

REPO = "https://github.com/example/graph"
IN_FORCE = (
    "refuses work",
    "does not accept work",
    "only while it has a steward",
    "only while a named",
)
ANNOUNCED = "not yet enforced"
PAGES = ("index.html", "problems/index.html", "about/index.html", "docs/index.html")


def pages(root) -> dict[str, str]:  # type: ignore[no-untyped-def]
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


@pytest.fixture(scope="module")
def announced(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    return pages(fixture.build(tmp_path_factory.mktemp("announced")))


@pytest.fixture(scope="module")
def enforced(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    return pages(fixture.build_with_stewards(tmp_path_factory.mktemp("enforced")))


def test_the_model_reads_the_switch(tmp_path_factory: pytest.TempPathFactory) -> None:
    plain = model.load_site(fixture.build(tmp_path_factory.mktemp("a")), fixture.COMMIT)
    ruled = model.load_site(
        fixture.build_with_stewards(tmp_path_factory.mktemp("b")), fixture.COMMIT
    )
    assert plain.steward_rule_enforced is False
    assert ruled.steward_rule_enforced is True


def test_an_unenforced_rule_is_announced_not_stated(announced: dict[str, str]) -> None:
    for rel in PAGES:
        html = announced[rel]
        for phrase in IN_FORCE:
            assert phrase not in html, (rel, phrase)
        assert ANNOUNCED in html, rel


def test_an_enforced_rule_is_stated(enforced: dict[str, str]) -> None:
    assert "refuses work" in enforced["about/index.html"]
    assert "does not accept work" in enforced["problems/index.html"]
    assert "only while it has a steward" in enforced["docs/index.html"]
    for rel in PAGES:
        assert ANNOUNCED not in enforced[rel], rel


def test_the_about_page_claims_only_the_signatures_the_record_shows(
    announced: dict[str, str],
) -> None:
    """The fixture's statements carry no non-author signature; the page must not say they do."""
    html = announced["about/index.html"]
    assert "is signed by someone who did not write it" not in html
    assert "graded unsigned until" in html
