"""F04-T50 (Q49): a statement's page reads top down, the way its panel does.

The owner, 2026-10-14, on erdos-1094--h1's page: "just like a wall of text, too much", to be
redesigned like the problem page's statement panel, with the explainer on top when one exists,
nothing redundant, and the detail linked or folded. Agreed layout: a header carrying the claim
(the math-first gloss, the Lean folded beneath); the explainer's overview, its steps folded; how
it was proved (one line, the outline and the Lean folded); what is known; work on it; and the
record, each part closed, holding everything else. A column of facts sits beside it (status,
target, depends on, proof, checks passed, submitter), and the attestation's table of checks is
folded into the record. The page stays the record: every link and every anchor today's page
carries is still on it (``node_page_baseline.json``, today's pages on this tree, captured before
the change).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import node_page_fixture as nf
import pytest
import summary_fixture as sf
from harness import TARGET
from panel_text import hrefs, visible_text, word_count

BASELINE = json.loads(
    (Path(__file__).parent / "node_page_baseline.json").read_text(encoding="utf-8")
)
#: Words a reader sees before opening anything, measured on this tree before the change
#: (root 614, first hole 347, second hole 270, interior node 265, tutorial 289): under half.
BUDGET = {nf.ROOT: 300, nf.H1: 170, nf.H2: 130, nf.MIDDLE: 130, nf.TUTORIAL: 140}


@pytest.fixture(scope="module")
def files(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    return nf.pages(tmp_path_factory.mktemp("node-page"))


def main(files: dict[str, str], node_id: str) -> str:
    return nf.main_of(nf.node_page(files, node_id))


def section(html: str, name: str) -> str:
    m = re.search(
        rf'<section class="node-sec[^"]*" data-section="{name}"[^>]*>(.*?)</section><!--/{name}-->',
        html,
        re.S,
    )
    assert m is not None, f"no {name} section"
    return m.group(1)


def at(html: str, name: str) -> int:
    return html.index(f'data-section="{name}"')


def header(html: str) -> str:
    m = re.search(r'<header class="node-head">(.*?)</header>', html, re.S)
    assert m is not None, "no header"
    return m.group(1)


def facts(html: str) -> dict[str, str]:
    m = re.search(r'<aside class="node-facts[^"]*"[^>]*>(.*?)</aside>', html, re.S)
    assert m is not None, "no facts column"
    pairs = re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", m.group(1), re.S)
    return {visible_text(k): visible_text(v) for k, v in pairs}


# --- the order -----------------------------------------------------------------------------------


def test_a_proved_node_with_an_explainer_leads_with_it(files: dict[str, str]) -> None:
    html = main(files, nf.ROOT)
    order = [at(html, s) for s in ("explainer", "how", "work", "record")]
    assert order == sorted(order), order
    assert html.index('<header class="node-head">') < order[0]
    assert "How it was proved" in section(html, "how")


def test_an_open_node_leads_with_how_it_is_being_proved(files: dict[str, str]) -> None:
    html = main(files, nf.H1)
    assert 'data-section="explainer"' not in html
    order = [at(html, s) for s in ("how", "known", "work", "record")]
    assert order == sorted(order), order
    assert "How it is being proved" in section(html, "how")


def test_a_proved_node_without_an_explainer_invites_one_under_work(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """The panel's tree has no explainer: its proved root invites one where the work is."""
    plain = sf.pages(sf.summary_tree(tmp_path_factory.mktemp("no-explainer")))
    html = nf.main_of(nf.node_page(plain, nf.ROOT))
    assert 'data-section="explainer"' not in html
    work = section(html, "work")
    assert "explainer" in visible_text(work).lower()
    assert ' id="explainer"' in work


# --- the header carries the claim ----------------------------------------------------------------


def test_a_math_first_gloss_is_the_claim_and_the_lean_is_folded(files: dict[str, str]) -> None:
    head = header(main(files, nf.H1))
    shown = visible_text(head)
    assert "p \\land q \\to q \\land p" in shown
    assert "unverified" in shown  # D-36: contributor words say so where they stand
    assert "theorem" not in shown  # the Lean is folded
    assert re.search(r"<details[^>]*>\s*<summary>[^<]*Lean", head)


def test_without_math_words_the_lean_is_the_claim(files: dict[str, str]) -> None:
    shown = visible_text(header(main(files, nf.H2)))
    assert "theorem" in shown


# --- the explainer -------------------------------------------------------------------------------


def test_the_explainer_shows_its_overview_and_folds_its_steps(files: dict[str, str]) -> None:
    ex = section(main(files, nf.ROOT), "explainer")
    shown = visible_text(ex)
    assert nf.OVERVIEW in shown
    assert "Regroup the three conjuncts" not in shown
    assert "Regroup the three conjuncts" in ex  # folded, not dropped
    assert "step by step" in shown
    assert "nverified" in shown  # D-36's label stays on the words


# --- the facts column ----------------------------------------------------------------------------


def test_the_facts_column_states_each_fact_once(files: dict[str, str]) -> None:
    html = main(files, nf.ROOT)
    f = facts(html)
    for key in ("status", "target", "depends on", "proof", "checked", "submitter"):
        assert key in f, (key, f)
    assert f["status"] == "proved"
    assert f["target"] == TARGET
    assert re.fullmatch(r"pass, \d+ of \d+ checks", f["checked"]), f["checked"]
    commit = f["proof"]
    assert re.fullmatch(r"[0-9a-f]{12}", commit), commit
    # The merge commit is named once in what the reader sees, not once per section.
    assert visible_text(html).count(commit) == 1


def test_an_open_node_has_no_proof_facts(files: dict[str, str]) -> None:
    f = facts(main(files, nf.H2))
    assert f["status"] == "open"
    assert "checked" not in f


# --- the record ----------------------------------------------------------------------------------


def test_the_attestation_table_is_folded_into_the_record(files: dict[str, str]) -> None:
    html = main(files, nf.ROOT)
    record = section(html, "record")
    assert '<table class="steps"' in record or "<table" in record
    assert html.count("<table") == record.count("<table")
    assert "kernel-replay" not in visible_text(html)


def test_empty_parts_of_the_record_are_not_shown(files: dict[str, str]) -> None:
    shown = visible_text(main(files, nf.H2))
    assert "No annex" not in shown
    assert "0 recorded" not in shown


def test_the_page_loads_the_script_that_opens_a_linked_fold(files: dict[str, str]) -> None:
    page = nf.node_page(files, nf.ROOT)
    assert '<script src="/node.js"' in page
    js = (Path(__file__).parents[1] / "opn_site" / "static" / "node.js").read_text("utf-8")
    assert "hashchange" in js
    assert "details" in js


# --- the budget, and nothing lost ----------------------------------------------------------------


@pytest.mark.parametrize("node_id", nf.NODES)
def test_the_page_shows_under_half_the_words(files: dict[str, str], node_id: str) -> None:
    n = word_count(main(files, node_id))
    assert n <= BUDGET[node_id], f"{node_id}: {n} visible words, budget {BUDGET[node_id]}"


@pytest.mark.parametrize("node_id", nf.NODES)
def test_no_link_is_lost(files: dict[str, str], node_id: str) -> None:
    now = hrefs(main(files, node_id))
    lost = set(BASELINE[node_id]["hrefs"]) - now
    assert not lost, lost
    # The panel's in-page links (``#node=``) mean nothing off the problem page.
    assert not [h for h in now if h.startswith("#node=")]


@pytest.mark.parametrize("node_id", nf.NODES)
def test_no_anchor_is_lost(files: dict[str, str], node_id: str) -> None:
    html = main(files, node_id)
    ids = set(re.findall(r' id="([^"]+)"', html))
    lost = set(BASELINE[node_id]["ids"]) - ids
    assert not lost, lost
    # Every in-page link the page itself carries lands somewhere on it.
    dangling = {h[1:] for h in hrefs(html) if h.startswith("#")} - ids
    assert not dangling, dangling


def test_every_link_into_the_page_lands(files: dict[str, str]) -> None:
    """The problem page's panel links a node's notes and words by anchor on the node's page."""
    problem = files[f"problems/{TARGET}/index.html"]
    for node_id in nf.NODES:
        page_path = f"/nodes/{TARGET}/{node_id}/"
        frags = {h.split("#", 1)[1] for h in hrefs(problem) if h.startswith(page_path + "#")}
        ids = set(re.findall(r' id="([^"]+)"', main(files, node_id)))
        assert frags <= ids, (node_id, frags - ids)
