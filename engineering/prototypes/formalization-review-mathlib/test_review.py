"""Checks on a finished Mathlib review (``out/results.json``) against ``manifest.json``.

These read the recorded results only. The first prototype re-ran every verdict in a local kernel;
here every verdict came from the network's hosted check (``POST /check``, anonymous limit 200 a
day), so re-running them would spend the budget twice. The Lean behind each verdict is kept in
the results (each discard's ``exhibit``, each pair's tactic or exhibit) and in ``exhibits/``.

    python3 review.py && .venv/bin/pytest engineering/prototypes/formalization-review-mathlib -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "manifest.json").read_text())
RESULTS = json.loads((HERE / "out" / "results.json").read_text())
TARGETS = [t for t in MANIFEST if not t.startswith("_")]
CASES = [(t, c) for t in TARGETS for c in MANIFEST[t]["candidates"]]


def main_cluster(t: str) -> list[str]:
    return next(cl for cl in RESULTS[t]["clusters"] if "incumbent" in cl)


@pytest.mark.parametrize(("t", "cid"), CASES)
def test_outcome_matches_manifest(t: str, cid: str) -> None:
    exp = MANIFEST[t]["candidates"][cid]["expect"]
    got = RESULTS[t]["candidates"][cid]
    in_main = got["status"] == "live" and cid in main_cluster(t)
    if exp == "survive":
        assert in_main, f"{cid}: {got['status']} {got.get('reason') or got.get('flag')}"
    elif exp == "discard-compile":
        assert got["status"] == "discarded" and got["stage"] == "compile", got
    elif exp == "discard-question":
        assert got["status"] == "discarded" and got["stage"].startswith("question"), got
    else:  # "caught": discarded, or left outside the main cluster with a flag for the signers
        assert not in_main, f"{cid} ({MANIFEST[t]['candidates'][cid].get('defect')}) was not caught"


@pytest.mark.parametrize("t", TARGETS)
def test_the_incumbent_survives_its_own_review(t: str) -> None:
    """The live statement, ported by a wrapper proved equal (Iff.rfl), passes every question."""
    assert RESULTS[t]["candidates"]["incumbent"]["status"] == "live"


@pytest.mark.parametrize("t", TARGETS)
def test_main_cluster_holds_an_agent_and_another_author(t: str) -> None:
    authors = {MANIFEST[t]["candidates"][c]["author"] for c in main_cluster(t)}
    assert "agent" in authors and len(authors) >= 2, authors


@pytest.mark.parametrize("t", TARGETS)
def test_every_survivor_outside_the_main_cluster_is_flagged(t: str) -> None:
    """Nothing is left live and unexplained: outside the main cluster means a flag for the signers."""
    main = main_cluster(t)
    for c, v in RESULTS[t]["candidates"].items():
        if v["status"] == "live" and c not in main:
            assert v.get("flag"), c


@pytest.mark.parametrize("t", TARGETS)
def test_every_discard_carries_its_reason_and_lean(t: str) -> None:
    for c, v in RESULTS[t]["candidates"].items():
        if v["status"] == "discarded":
            assert v.get("reason"), c
            assert v.get("exhibit") or v["stage"] == "compile", c


@pytest.mark.parametrize("t", TARGETS)
def test_every_question_was_answered_and_tested(t: str) -> None:
    r = RESULTS[t]
    assert len(r["questions"]) == len(r["tests"])
    for q, tt in zip(r["questions"], r["tests"]):
        assert q["key"] == tt["key"] and q["answer"] == tt["expected"]


@pytest.mark.parametrize("t", TARGETS)
def test_no_mutant_missed(t: str) -> None:
    assert not [m for m in RESULTS[t]["mutants"] if m["result"] == "missed"]


def test_no_open_pair_is_reported_as_a_difference() -> None:
    """D-9 v3.12: a failed proof is inconclusive; only 'proved' or 'open' are recorded here."""
    for t in TARGETS:
        assert {p["state"] for p in RESULTS[t]["pairs"].values()} <= {"proved", "open"}


def test_calls_stayed_inside_the_anonymous_limit() -> None:
    assert len(RESULTS["_calls"]) <= 160
