"""F15-T10 / AC10: what the site shows for stewards, the digestion state, a signed explainer and
a calibration target (R10; D-36 v3.17)."""

from __future__ import annotations

from html import escape

import pytest
from fixture import (
    CALIBRATION_TARGET,
    COMMIT,
    RESOLVED_TARGET,
    SIGNER_LOGIN,
    STEWARD_LINK,
    STEWARD_LOGIN,
    STEWARD_NAME,
    STEWARDED_TARGET,
    STEWARDLESS_TARGET,
    build_with_stewards,
)

from opn_gate import intake
from opn_site import model, render

REPO = "https://github.com/example/graph"


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = build_with_stewards(tmp_path_factory.mktemp("stewards"))
    site = model.load_site(root, COMMIT)
    return render.render_site(site, repo_url=REPO)


def target_page(pages: dict[str, str], target_id: str) -> str:
    return pages[f"problems/{target_id}/index.html"]


def card(pages: dict[str, str], target_id: str) -> str:
    page = pages["problems/index.html"]
    start = page.index('<article class="card problem" data-status="')
    while f'id="p-{target_id}"' not in page[start : page.index(">", start)]:
        start = page.index('<article class="card problem"', start + 1)
    return page[start : page.index("</article>", start)]


def test_the_stewarded_target_names_its_steward(pages: dict[str, str]) -> None:
    """R10: the steward by name and link, with the date they committed; the name is escaped and
    the link is the record's; the Targets row carries the same; the target is claimable."""
    page = target_page(pages, STEWARDED_TARGET)
    assert f'<a href="{STEWARD_LINK}">{escape(STEWARD_NAME)}</a>' in page
    assert "<b>not bold</b>" not in page
    assert f"<code>{STEWARD_LOGIN}</code>" in page and "committed 2026-09-16" in page
    assert "This problem is open for work." in page
    row = card(pages, STEWARDED_TARGET)
    assert f'Steward · <a href="{STEWARD_LINK}">{escape(STEWARD_NAME)}</a>' in row
    assert 'data-status="open"' in row and row.count('class="stage off"') == 3


def test_the_stewardless_target_says_so_in_words(pages: dict[str, str]) -> None:
    """R10: the cue saying what a steward commits to and receives, linked to the Docs section,
    and the no-steward reason in the Targets page's words."""
    page = target_page(pages, STEWARDLESS_TARGET)
    assert "No steward yet." in page and 'href="/docs/#stewards"' in page
    assert "commits to understand and write up" in page
    assert escape(intake.explain("no-steward")) in page
    assert "Not claimable" in page
    row = card(pages, STEWARDLESS_TARGET)
    assert 'data-status="needs a steward"' in row and ">Needs a steward</span>" in row
    assert escape(intake.explain("no-steward")) in row  # the status tag's hover card
    # The root's node page and the frontier row say the same (F04-T10).
    node = pages[f"nodes/{STEWARDLESS_TARGET}/stewardless-lemma/index.html"]
    assert escape(intake.explain("no-steward")) in node


def test_the_resolved_target_shows_its_digestion_state(pages: dict[str, str]) -> None:
    """R10: the lead "resolved — undigested" and the report-back sentence D-10 carries."""
    page = target_page(pages, RESOLVED_TARGET)
    assert 'tabindex="0">proved<span class="term-card"' in page
    assert "None yet" in page and "proved but not explained" in page
    assert "Resolved — <strong>undigested</strong>" in page
    assert "kernel-checked, not yet explained" in page
    assert "0 of 1 proved nodes in the closing proof" in page
    assert "No paper or note recorded yet (D-32)." in page
    assert "No stewards: this target is not an open problem" in page
    row = card(pages, RESOLVED_TARGET)
    assert 'data-status="proved"' in row
    assert '<span class="stage on"><span class="dot dot-proved"></span>Proved</span>' in row
    assert '<span class="stage off"><span class="dot dot-blocked"></span>Explained</span>' in row
    assert "Steward wanted for write-up" in row


def test_the_calibration_target_is_labelled(pages: dict[str, str]) -> None:
    page = target_page(pages, CALIBRATION_TARGET)
    assert "A calibration target" in page and "Stages v3.17" in page
    assert "Calibration target, no steward needed" in card(pages, CALIBRATION_TARGET)
    assert "This problem is open for work." in page  # exempt from the steward rule (R4)
    for other in (STEWARDED_TARGET, STEWARDLESS_TARGET, RESOLVED_TARGET):
        assert "A calibration target:" not in target_page(pages, other)


def test_the_signed_explainer_is_vouched_for_above_the_label(pages: dict[str, str]) -> None:
    """R10: "explained and vouched for by name, date" above the unverified label, linked to the
    signature file; a node with no signature carries no such line."""
    page = pages["nodes/propositional/and-reassoc/index.html"]
    vouched = page.index("Explained and vouched for by")
    assert vouched < page.index("Unverified: explainer")
    assert f"<strong>{SIGNER_LOGIN}</strong>, 2026-09-16" in page
    assert "/explainer/signed/" in page[vouched : vouched + 800]
    unsigned = pages["nodes/propositional/tutorial-and-swap/index.html"]
    assert "vouched for" not in unsigned and "Unverified: explainer" in unsigned


def test_the_home_counts_lead_with_coverage(pages: dict[str, str]) -> None:
    """R10, Q10: the counts card leads with explained / proved (F04-T12's big number), and the
    steward count is of distinct stewards."""
    home = pages["index.html"]
    assert '<span class="big">1 / 3</span>' in home
    assert "proved statements explained" in home
    assert '<span class="n">1</span><span class="l">stewards</span>' in home


def test_every_new_link_is_on_the_allowlist(pages: dict[str, str]) -> None:
    """R13, F15 §7: the steward's link and the docs anchor are the only new links, and the
    renderer got them from validated records (the build would have refused otherwise)."""
    assert STEWARD_LINK in target_page(pages, STEWARDED_TARGET)
    assert "docs/index.html" in pages
