"""F22-T17: the testers' small site findings (bugs.md P3 8, 9, 10, 14, 15).

- (8) A spec-* panel read "A statement the proof needs; proved." above "Not needed by any proof of
  this problem": an authored node's role claimed a use only the proof row may state.
- (9) "Read proof 1 top-down" opened a page headed "The proof, dependencies first".
- (10) Below 900px the "statement unchecked" badge was hidden, so phones lost the fidelity
  warning.
- (14) "drafted with …" was printed twice for each version: on the provenance line and again on
  each section's state chip.
- (15) A library constant's docstring in a hover card showed raw backticks and ``**``.
"""

from __future__ import annotations

import re
from html import escape

import fixture
import gloss_fixture as gf
import pytest
from harness import TARGET

from opn_site import model, render

REPO = "https://github.com/example/graph"


# --- (8) ------------------------------------------------------------------------------------------


def test_an_authored_statement_does_not_claim_the_proof_needs_it() -> None:
    assert "need" not in render.ORIGIN_ROLES["authored"]
    assert render.ORIGIN_ROLES["authored"] == "proposed by a contributor"


# --- (9) ------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def chain_pages(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    import reading_fixture as rf  # noqa: PLC0415

    root = rf.chain_tree(tmp_path_factory.mktemp("small-items"))
    return render.render_site(model.load_site(root, fixture.COMMIT), repo_url=REPO)


def test_the_reading_link_names_the_order_the_page_uses(chain_pages: dict[str, str]) -> None:
    problem = chain_pages[f"problems/{TARGET}/index.html"]
    links = re.findall(r'<a href="(/problems/[^"]+/proofs/[^"]+)">(Read proof[^<]*)</a>', problem)
    assert links, "no reading link"
    for href, text in links:
        assert "top-down" not in text
        assert "dependencies first" in text
        page = chain_pages[href.strip("/") + "/index.html"]
        assert "dependencies first" in page


# --- (10) -----------------------------------------------------------------------------------------


def test_the_fidelity_badge_is_not_hidden_on_phones() -> None:
    css = (render.STATIC / "site.css").read_text(encoding="utf-8")
    for rule in re.findall(r"([^{}]+)\{\s*display:\s*none;?\s*\}", css):
        assert ".tag-outline" not in rule, rule.strip()


# --- (14) -----------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def sectioned(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    root, _ = gf.sectioned_tree(tmp_path_factory.mktemp("sectioned"))
    return render.render_site(model.load_site(root, gf.COMMIT), repo_url=REPO)


def test_drafted_with_is_said_once_per_version(sectioned: dict[str, str]) -> None:
    page = sectioned[f"nodes/{TARGET}/{gf.TUTORIAL}/index.html"]
    model_words = f"drafted with {escape(gf.DRAFTED_WITH)}"
    blocks = re.findall(
        r'<div class="prose-block unverified explainer-version".*?<p class="gloss-foot">',
        page,
        re.S,
    )
    assert blocks
    for block in blocks:
        assert block.count(model_words) <= 1, block[:400]
    chips = re.findall(r'<p class="words-state" data-state="drafted">(.*?)</p>', page, re.S)
    assert chips
    for chip in chips:
        assert "drafted with" not in chip


# --- (15) -----------------------------------------------------------------------------------------


def test_a_docstring_card_renders_its_code_spans() -> None:
    r = render.Renderer.__new__(render.Renderer)
    step = {
        "uses": {
            "nodes": [],
            "defs": [],
            "mathlib": [{"name": "one_pos", "doc": "**Alias** of `zero_lt_one`.", "tags": []}],
        }
    }
    html = r.step_uses(None, step)  # type: ignore[arg-type]
    card = re.search(r'<span class="term-card" role="tooltip">(.*?)</span>', html, re.S)
    assert card is not None
    assert card.group(1) == "<strong>Alias</strong> of <code>zero_lt_one</code>."
