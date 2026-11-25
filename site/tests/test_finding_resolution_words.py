"""F04-T31 (audit follow-up to F03-T17, D-33 as written, decisions v3.28): the site says how a
problem was resolved.

Since F03-T17 a target is ``resolved`` when its root is proved, refuted (a merged counterexample)
or defective (a merged vacuity certificate). The site turned ``resolved`` into the word "proved"
wherever it named a problem's status — the status tag, the Problems filter, the stage marks, the
problem page's sentence and its steward card — so a conjecture a counterexample had settled read
"proved", which is false. The words now follow the root's status in ``graph.json``: proved reads
"proved", refuted "disproved" (a counterexample is on the record), defective "shown ill-posed" (a
vacuity certificate is on the record). The last test holds the site's words to the products, the
way the site's workable set is held to the frontier.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fixture import COMMIT, RESOLUTIONS, build_with_resolutions
from problem_rows import problem_row

from opn_gate import graph
from opn_site import model, render

REPO = "https://github.com/example/graph"
SETTLED = RESOLUTIONS
EXPECTED = {
    "proved-target": "proved",
    "disproved-target": "disproved",
    "ill-posed-target": "shown ill-posed",
}


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, str]]:
    """Three open-track targets, each resolved by a different root-level D-12 artifact
    (``fixture.build_with_resolutions``), and the site rendered from their products."""
    root = build_with_resolutions(tmp_path_factory.mktemp("resolution"))
    return root, render.render_site(model.load_site(root, COMMIT), repo_url=REPO)


def card(page: str, tid: str) -> str:
    """The problem's row, from its opening tag (which carries ``data-status``) to its close
    (F34-T5: a row of the Problems page, no longer a card)."""
    return problem_row(page, tid)


def target_page(files: dict[str, str], tid: str) -> str:
    return files[f"problems/{tid}/index.html"]


def test_the_fixture_resolves_all_three(built: tuple[Path, dict[str, str]]) -> None:
    root, _files = built
    rows = json.loads((root / "targets" / "index.json").read_text())["targets"]
    status = {r["target_id"]: r["status"] for r in rows}
    for tid in SETTLED:
        assert status[tid] == "resolved", tid
    roots = {tid: graph.load_target(root, tid) for tid in SETTLED}
    assert [roots[t].statuses[roots[t].root] for t in SETTLED] == ["proved", "refuted", "defective"]


@pytest.mark.parametrize("tid", ["disproved-target", "ill-posed-target"])
def test_a_problem_settled_against_its_statement_does_not_read_proved(
    built: tuple[Path, dict[str, str]], tid: str
) -> None:
    """The red case: a merged counterexample (or vacuity certificate) on the root, and the card,
    the tag and the problem page said "proved"."""
    _root, files = built
    word = EXPECTED[tid]
    c = card(files["problems/index.html"], tid)
    assert f'data-status="{word}"' in c
    assert re.search(rf'<span class="term tag" tabindex="0">{word}<span class="term-card"', c)
    # F34-T5: the stage mark is three dots now; its words name the resolution, never "proved"
    assert 'aria-label="proved: yes' not in c
    assert f'aria-label="{word}: yes' in c
    page = target_page(files, tid)
    assert "Proved:" not in page and "is proved but not explained" not in page
    assert f"{word.capitalize()}:" in page
    assert f"is {word} but not explained" in page
    # F34-T11: the heading sits under §6 Record now, an h3
    assert "<h3>Proved, explained, written up</h3>" not in page
    assert f"<h3>{word.capitalize()}, explained, written up</h3>" in page


def test_each_resolution_says_what_is_on_the_record(built: tuple[Path, dict[str, str]]) -> None:
    _root, files = built
    assert "a counterexample is on the record" in target_page(files, "disproved-target")
    assert "a vacuity certificate is on the record" in target_page(files, "ill-posed-target")
    assert "a proof is on the record" in target_page(files, "proved-target")


def test_a_proved_problem_still_reads_proved(built: tuple[Path, dict[str, str]]) -> None:
    _root, files = built
    c = card(files["problems/index.html"], "proved-target")
    assert 'data-status="proved"' in c and "proved: yes" in c  # the stage mark's words
    assert "Proved:" in target_page(files, "proved-target")


def test_the_proved_filter_counts_only_proved_problems(built: tuple[Path, dict[str, str]]) -> None:
    """F34-T5: the Status filter's "Proved" keeps ``data-stage="proved"`` (every resolved
    problem), and the word each row shows stays the resolution's: only a problem proved
    against its statement reads ``data-status="proved"``. The page prints no count beside the
    filter (handoff §6), so the two sets are held apart here instead."""
    _root, files = built
    page = files["problems/index.html"]
    assert 'data-stage="proved"' in page
    for tid, word in EXPECTED.items():
        row = card(page, tid)
        assert 'data-stage="proved"' in row, tid
        assert f'data-status="{word}"' in row, tid


def test_the_site_words_follow_the_products(built: tuple[Path, dict[str, str]]) -> None:
    """Held to the products: every resolved problem's word is the one its root's status in
    ``graph.json`` calls for, read from the files the site renders from, and every other word is
    not one of the three."""
    root, files = built
    page = files["problems/index.html"]
    rows = json.loads((root / "targets" / "index.json").read_text())["targets"]
    for row in rows:
        tid = str(row["target_id"])
        doc = json.loads((root / "targets" / tid / "graph.json").read_text())
        root_status = next(n["status"] for n in doc["nodes"] if n["node_id"] == doc["root"])
        word = re.search(r'data-status="([^"]+)"', card(page, tid))
        assert word is not None
        if row["status"] == "resolved":
            assert word.group(1) == render.RESOLUTION_WORDS.get(root_status, "proved"), tid
        else:
            assert word.group(1) not in ("proved", *render.RESOLUTION_WORDS.values()), tid


def test_every_resolution_word_is_defined_and_keyed() -> None:
    """A new word gets a definition, a Docs key item and a Glossary row."""
    for word in ("proved", *render.RESOLUTION_WORDS.values()):
        assert word in render.PROBLEM_STATUS_DEFS, word
        assert word in render.STATE_MAP_PROBLEM_KEYS, word
    labels = {label for _k, label, _m, _p in render.GLOSSARY}
    for word in render.RESOLUTION_WORDS.values():
        assert word in labels, word


def test_a_resolved_problem_does_not_say_a_proof_waits_for_review(
    built: tuple[Path, dict[str, str]],
) -> None:
    """F04-T32: once a problem is resolved, its root is settled and a further proof of it merges
    as an alternate, which step 9 does not ask (D-3 v3.13); nothing beneath it waits either
    (v3.20). The page said "A proof of this statement waits for a non-author's approving review"
    on every resolved problem whose root had no certificate or evidence."""
    _root, files = built
    for tid in SETTLED:
        page = target_page(files, tid)
        assert "waits for a non-author" not in page, tid
        assert "merges as an alternate" in page, tid
