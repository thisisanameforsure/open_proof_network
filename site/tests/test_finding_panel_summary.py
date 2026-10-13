"""F04-T48 (Q47): the statement panel is a summary for a mathematician surveying the problem.

The owner, 2026-10-13: the panel on the problem page had grown into the record — the Lean, a
``:= by sorry`` paragraph, untrusted-text disclaimers, the whole gloss with its provenance, every
outline's checklist — and a reader surveying erdos-1094 had to read 700 words to learn what a
hole claims. Now the panel reads top to bottom as: who it is (id, status, attempts, one line of
role), **what is claimed** (a math-first gloss's opening math and its convention notes, the Lean
folded; or the Lean itself with "Explain this"), **how it is being proved** (the split, or one
line naming the proof, or one line saying it is open), **what is known** (the literature status in
one line, the notes by their first sentence), **work on it** (the plans by their first sentence,
whether a decomposition followed each, the target's approach records on the root, the action),
and the record details, closed, holding everything else. Nothing is lost: every link today's
panel carried is still in the panel or on the statement's own page (``panel_summary_baseline.json``
is today's panel on this tree, captured before the change).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import summary_fixture as sf
from harness import TARGET
from panel_text import hrefs, unhidden, visible_text, word_count
from test_outline_links import panel

from opn_site import prose, render

BASELINE = json.loads(
    (Path(__file__).parent / "panel_summary_baseline.json").read_text(encoding="utf-8")
)
#: Visible words (outside closed details) on today's panel, measured on this tree before the
#: change (task-48.txt): root 345, first hole 181, second hole 104. The budget is half.
BUDGET = {sf.ROOT: 172, sf.H1: 90, sf.H2: 52}
SECTIONS = ("claim", "how", "known", "work")


@pytest.fixture(scope="module")
def files(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    return sf.pages(sf.summary_tree(tmp_path_factory.mktemp("summary")))


def body(files: dict[str, str], node_id: str) -> str:
    return unhidden(panel(sf.problem_page(files), node_id))


def section(html: str, name: str) -> str:
    m = re.search(
        rf'<section class="panel-sec" data-section="{name}">(.*?)</section>\n', html, re.S
    )
    assert m is not None, f"no {name} section"
    return m.group(1)


def record(html: str) -> str:
    m = re.search(r'<details class="record">.*</details>', html, re.S)
    assert m is not None, "no record details"
    return m.group(0)


def test_the_sections_come_in_the_owners_order(files: dict[str, str]) -> None:
    html = body(files, sf.ROOT)
    at = [html.index(f'data-section="{s}"') for s in SECTIONS]
    assert at == sorted(at), at
    assert html.index('class="panel-facts"') < at[0]  # the header first
    assert at[-1] < html.index('<details class="record">')  # the record details last
    for s, kicker in zip(
        SECTIONS,
        ("What is claimed", "How it is being proved", "What is known", "Work on it"),
        strict=True,
    ):
        assert kicker in section(html, s)


def test_a_math_first_gloss_is_the_headline_and_the_lean_is_folded(files: dict[str, str]) -> None:
    claim = section(body(files, sf.H1), "claim")
    shown = visible_text(claim)
    assert "p \\land q \\to q \\land p" in shown
    assert "Lean writes the swap with" in shown  # the convention notes follow the math
    assert 'class="math' in claim
    fold = re.search(
        r'<details class="panel-lean"><summary>Lean</summary>(.*?)</details>', claim, re.S
    )
    assert fold is not None, "the Lean is not folded"
    assert '<pre class="lean statement' in fold.group(1)
    assert "theorem" not in shown  # the Lean is not visible until the fold opens
    assert "unverified" in shown
    assert f'href="/nodes/{TARGET}/{sf.H1}/#statement-words"' in claim  # the mark's history


def test_lean_only_shows_the_lean_and_explain_this(files: dict[str, str]) -> None:
    claim = section(body(files, sf.H2), "claim")
    shown = visible_text(claim)
    assert "theorem and_swap_reassoc__h2" in shown
    assert "panel-lean" not in claim
    link = re.search(r'<a class="explain-this" href="([^"]+)">Explain this', claim)
    assert link is not None, "no Explain this"
    assert link.group(1) == f"/nodes/{TARGET}/{sf.H2}/#statement-words"
    # The node page holds the anchor: its statement block, with the full Lean, the words, and the
    # cue linking the guide's walk-through for writing them.
    node = sf.node_page(files, sf.H2)
    at = node.find('id="statement-words"')
    assert at != -1, "the node page has no #statement-words"
    block = node[at : node.index("<h2>Proof</h2>", at)]
    assert '<pre class="lean statement' in block
    assert "How to write one" in block and 'href="/docs/#guide-glosses' in block


def test_a_gloss_that_is_not_math_first_is_compact_and_unverified(tmp_path: Path) -> None:
    import gloss_fixture as gf  # noqa: PLC0415

    root = sf.summary_tree(tmp_path)
    gf.gloss(
        root,
        "In words: the second half holds. A second sentence that stays on the node page.",
        kind="statement",
        node=sf.H2,
        author="bob",
    )
    claim = section(unhidden(panel(sf.problem_page(sf.pages(root)), sf.H2)), "claim")
    shown = visible_text(claim)
    assert "theorem and_swap_reassoc__h2" in shown  # the Lean still leads
    assert "In words: the second half holds." in shown
    assert "A second sentence" not in shown
    assert "unverified" in shown
    assert shown.index("theorem") < shown.index("In words")
    assert 'class="explain-this"' in claim


def test_the_how_section_names_the_proof_or_says_it_is_open(files: dict[str, str]) -> None:
    how = visible_text(section(body(files, sf.ROOT), "how"))
    assert "Proved by Proof.lean" in how and "attestation" in how
    assert "Split into" in how
    hole = visible_text(section(body(files, sf.H1), "how"))
    assert hole == "How it is being proved Open. A direct proof closes it."
    assert render.Renderer.open_line(has_holes=True) == (
        "Open. A direct proof, or proofs of its holes, close it."
    )


def test_the_known_section_is_one_literature_line_and_the_notes_by_first_sentence(
    files: dict[str, str],
) -> None:
    known = section(body(files, sf.H1), "known")
    shown = visible_text(known)
    assert "Literature: Open problem: no proof is known" in shown
    assert "proposed by t1009-b" in shown
    assert sf.LITERATURE_SUMMARY not in shown  # the summary and references are folded
    assert sf.LITERATURE_SUMMARY.replace("'", "&#x27;") in known or sf.LITERATURE_SUMMARY in known
    root = section(body(files, sf.ROOT), "known")
    shown = visible_text(root)
    assert "Numerical check, 2026-10-12." in shown
    assert "The hypotheses were tested" not in shown  # only the first sentence
    assert f'href="/nodes/{TARGET}/{sf.ROOT}/#annex-{sf.NOTE[:12]}"' in root


def test_the_work_section_lists_the_plans_and_the_approach_records_on_the_root(
    files: dict[str, str],
) -> None:
    work = section(body(files, sf.ROOT), "work")
    shown = visible_text(work)
    assert "Split the claim at the conjunction: first $p$, then $q$." in shown
    assert "Each half is then a hole" not in shown
    assert "followed by " + sf.PARTIAL_NAME in shown
    assert sf.APPROACH in shown
    assert "View the proof" in shown
    hole = section(body(files, sf.H1), "work")
    assert sf.APPROACH not in hole  # a target's approach records name no node (Q47)
    assert "Work on this statement" in visible_text(hole)


@pytest.mark.parametrize("node_id", [sf.ROOT, sf.H1, sf.H2])
def test_the_visible_panel_is_within_its_word_budget(files: dict[str, str], node_id: str) -> None:
    n = word_count(body(files, node_id))
    assert n <= BUDGET[node_id], f"{node_id}: {n} visible words (budget {BUDGET[node_id]})"


BOILERPLATE = (
    "the <code>sorry</code> holds the place of a proof",
    "A hole&rsquo;s words are the opening math of its gloss",
    "Untrusted contributor text (D-31)",
    "the partial proof assumes each and proves this statement from them",
)


@pytest.mark.parametrize("node_id", [sf.ROOT, sf.H1])
def test_boilerplate_is_out_of_sight_but_in_the_record_details(
    files: dict[str, str], node_id: str
) -> None:
    html = body(files, node_id)
    shown = visible_text(html)
    details = record(html)
    for words in BOILERPLATE:
        plain = visible_text(words)
        assert plain not in shown, words
    assert 'href="/docs/#reading"' in details  # how to read this
    if node_id == sf.ROOT:
        for words in BOILERPLATE:
            assert words in details, words


@pytest.mark.parametrize("node_id", [sf.ROOT, sf.H1, sf.H2])
def test_no_link_is_lost(files: dict[str, str], node_id: str) -> None:
    now = hrefs(body(files, node_id)) | hrefs(sf.node_page(files, node_id))
    lost = set(BASELINE[node_id]["hrefs"]) - now
    assert not lost, lost


def test_first_sentence_stops_before_a_closing_emphasis() -> None:
    assert prose.first_sentence("**Numerical check, 2026-10-12.** The rest.") == (
        "**Numerical check, 2026-10-12.**"
    )
    assert prose.first_sentence("*One.* Two.") == "*One.*"
    assert prose.first_sentence("Plain. Two.") == "Plain."
