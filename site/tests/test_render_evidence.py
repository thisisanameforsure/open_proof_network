"""F14-T7: the target page and the Targets row show the evidence and what a proof needs (R10;
AC10).

A reader sees, for a curated root, the catalog score and the reasons that sum to it, the registry
history, the hazards, each second formalization with its equivalence verdict, and one sentence
saying whether a proof merges on the gate or waits for a person. A listed target is claimable, so
neither page says otherwise.
"""

from __future__ import annotations

from html import escape

import pytest
from fixture import (
    COMMIT,
    EVIDENCE_INJECTION,
    LISTED_ROOT,
    LISTED_TARGET,
    build_with_evidenced_target,
)

from opn_site import model, render

REPO = "https://github.com/example/graph"
TARGET_PAGE = f"targets/{LISTED_TARGET}/index.html"


@pytest.fixture(scope="module")
def pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root = build_with_evidenced_target(tmp_path_factory.mktemp("evidenced"))
    return render.render_site(model.load_site(root, COMMIT), repo_url=REPO)


def card(page: str, target_id: str) -> str:
    [found] = [c for c in page.split('<section class="target-card">')[1:] if f">{target_id}<" in c]
    return found


def test_the_target_page_shows_the_evidence(pages: dict[str, str]) -> None:
    page = pages[TARGET_PAGE]
    assert "Catalog evidence (F14): score <strong>6</strong> (A)" in page
    assert "<code>erdos:42</code>" in page and "pinned to the root as it stands" in page
    assert "+2 Bloom selected it for FrontierMath Erdős" in page
    assert "In the registry since 2025-04-26, last changed 2026-07-16, 13 commits." in page
    assert "No misformalization issue on record." in page
    assert "Wording hazards: density." in page


def test_the_evidence_is_escaped(pages: dict[str, str]) -> None:
    page = pages[TARGET_PAGE]
    assert EVIDENCE_INJECTION not in page
    assert escape(EVIDENCE_INJECTION) in page


def test_the_target_page_says_a_proof_merges_on_the_gate(pages: dict[str, str]) -> None:
    page = pages[TARGET_PAGE]
    assert (
        "A proof of this statement merges on the gate without a human reviewer: its recorded "
        "catalog evidence scores 6 (A)"
    ) in page
    assert "Not claimable" not in page


def test_the_formalization_and_its_verdict_are_listed(pages: dict[str, str]) -> None:
    page = pages[TARGET_PAGE]
    assert "Second formalizations of this conjecture" in page
    assert "<code>alt</code>: equivalence with the root <strong>pass</strong>" in page
    assert "qa/exhibits/root-equivalence-1.lean" in page
    frontier = pages["frontier/index.html"]
    assert ">alt</a>" not in frontier, "a formalization is never a frontier row (F14-R7)"
    assert f"nodes/{LISTED_TARGET}/alt/index.html" not in pages


def test_the_targets_row_carries_the_review_sentence(pages: dict[str, str]) -> None:
    row = card(pages["targets/index.html"], LISTED_TARGET)
    assert "<dt>Review</dt><dd>A proof of this statement merges on the gate" in row
    assert "<dt>Status</dt><dd>listed, claimable</dd>" in row
    assert "Not claimable" not in row


def test_a_root_without_evidence_waits_for_a_person(pages: dict[str, str]) -> None:
    """The propositional target has no certificate and no evidence: a proof waits for review."""
    page = pages["targets/propositional/index.html"]
    assert "waits for a non-author&#x27;s approving review" in page or (
        "waits for a non-author's approving review" in page
    )


def test_a_node_page_under_the_evidenced_target_is_claimable(pages: dict[str, str]) -> None:
    page = pages[f"nodes/{LISTED_TARGET}/{LISTED_ROOT}/index.html"]
    assert "Not claimable" not in page
