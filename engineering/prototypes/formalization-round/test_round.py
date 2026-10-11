"""Checks on a finished round (``out/results.json``), against ``manifest.json`` and the kernel.

The outcome tests read the results. The soundness tests do not trust them: they re-run Lean on
every discard and every survivor, so a bookkeeping bug in ``round.py`` cannot pass for a catch.

    python3 round.py && .venv/bin/pytest engineering/prototypes/formalization-round -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import round as R  # noqa: E402

MANIFEST = json.loads((HERE / "manifest.json").read_text())
RESULTS = json.loads((HERE / "out" / "results.json").read_text())
CONJS = [c for c in MANIFEST if not c.startswith("_")]
CASES = [(cj, cid) for cj in CONJS for cid in MANIFEST[cj]["candidates"]]


def main_cluster(cj: str) -> list[str]:
    r = RESULTS[cj]
    return next(cl for cl in r["clusters"] if "human-ref" in cl)


def src(cj: str, cid: str) -> str:
    return (HERE / "candidates" / cj / f"{cid}.lean").read_text()


@pytest.mark.parametrize(("cj", "cid"), CASES)
def test_outcome_matches_manifest(cj: str, cid: str) -> None:
    exp = MANIFEST[cj]["candidates"][cid]["expect"]
    got = RESULTS[cj]["candidates"][cid]
    in_main = got["status"] == "live" and cid in main_cluster(cj)
    if exp == "survive":
        assert in_main, f"{cid} should be in the main cluster: {got['status']} {got.get('reason') or got.get('flag')}"
    elif exp == "discard-compile":
        assert got["status"] == "discarded" and got["stage"] == "compile"
    elif exp == "returned":
        assert got["status"] == "returned" and got["stage"] == "format", got
    else:  # every planted defect, and every reading the proposer rules out, must end outside it
        assert not in_main, f"{cid} ({MANIFEST[cj]['candidates'][cid].get('defect')}) was not caught"


@pytest.mark.parametrize("cj", CONJS)
def test_one_cluster_survives(cj: str) -> None:
    live = [c for c, v in RESULTS[cj]["candidates"].items() if v["status"] == "live"]
    assert sorted(live) == sorted(main_cluster(cj)), RESULTS[cj]["clusters"]


@pytest.mark.parametrize("cj", CONJS)
def test_main_cluster_has_a_person_and_an_agent(cj: str) -> None:
    authors = {MANIFEST[cj]["candidates"][c]["author"] for c in main_cluster(cj)}
    assert {"human", "agent"} <= authors


@pytest.mark.parametrize("cj", CONJS)
def test_every_mutant_that_changes_meaning_is_caught(cj: str) -> None:
    bad = [m for m in RESULTS[cj]["mutants"] if m["result"] == "missed"]
    assert not bad, bad


@pytest.mark.parametrize("cj", CONJS)
def test_main_cluster_is_connected_by_proved_pairs(cj: str) -> None:
    """Re-derive the cluster from the recorded pairs: a chain of directions proved both ways."""
    cl, pairs = main_cluster(cj), RESULTS[cj]["pairs"]
    reach, frontier = {cl[0]}, [cl[0]]
    while frontier:
        a = frontier.pop()
        for b in cl:
            if b not in reach and pairs[f"{a}→{b}"]["state"] == pairs[f"{b}→{a}"]["state"] == "proved":
                reach.add(b)
                frontier.append(b)
    assert reach == set(cl)


def test_no_failed_attempt_is_recorded_as_refuted() -> None:
    """D-9 v3.12: a failure is inconclusive. 'refuted' only with a kernel-checked instance."""
    for cj in CONJS:
        for key, p in RESULTS[cj]["pairs"].items():
            assert p["state"] in {"proved", "refuted", "open"}
            if p["state"] == "refuted":
                assert "n" in p and "decide +kernel" in p["lean"], key


DISCARDS = [(cj, cid) for cj in CONJS for cid, v in RESULTS[cj]["candidates"].items()
            if v["status"] == "discarded" and v["stage"] not in ("compile", "format")]


@pytest.mark.parametrize(("cj", "cid"), DISCARDS)
def test_every_discard_is_reproduced_by_the_kernel(cj: str, cid: str) -> None:
    """Re-run the Lean that discarded it, independently of round.py's bookkeeping."""
    v = RESULTS[cj]["candidates"][cid]
    s = src(cj, cid)
    if v["stage"] == "screen":
        ex = HERE / "exhibits" / cj / f"{cid}.lean"
        body = R.wrap(cid, s + "\n" + ex.read_text()) if v["screen"]["by"] == "agent exhibit" else (
            R.wrap(cid, s) + v["screen"]["lean"] + "\n")
        ok, out = R.lean(body)
        assert ok, out[-600:]
        return
    # an intent test: find the test that failed for it, and check the kernel says the opposite
    failed = [t for t in RESULTS[cj]["tests"] if t["results"].get(cid) is False]
    assert failed, f"{cid} discarded with no failing test recorded"
    t = failed[0]
    k, exp = t["n"], t["expected"]
    if t["kind"] == "holds":
        ok, _ = R.kernel_check(cid, s, k, not exp)
    elif t["kind"] == "covers":
        ok, _ = R.kernel_check(cid, R.counterfactual(s), k, exp)
    elif t["kind"] == "witness":
        ok, _ = R.probe_check(cid, s, tuple(t["concept"]), k, not exp)
    else:
        hs = [h for h, c in v["helpers"].items() if c == t["concept"]]
        ok = any(R.concept_check(cid, s, h, k, not exp)[0] for h in hs)
    assert ok, f"the kernel does not confirm {cid} disagrees with the proposer on {t}"


SURVIVORS = [(cj, cid) for cj in CONJS for cid, v in RESULTS[cj]["candidates"].items()
             if v["status"] == "live"]


@pytest.mark.parametrize(("cj", "cid"), SURVIVORS)
def test_every_survivor_passes_every_intent_test_in_the_kernel(cj: str, cid: str) -> None:
    s = src(cj, cid)
    v = RESULTS[cj]["candidates"][cid]
    for t in RESULTS[cj]["tests"]:
        k, exp = t["n"], t["expected"]
        if t["kind"] == "holds":
            ok, _ = R.kernel_check(cid, s, k, exp)
        elif t["kind"] == "covers":
            ok, _ = R.kernel_check(cid, R.counterfactual(s), k, not exp)
        elif t["kind"] == "witness":
            ok, _ = R.probe_check(cid, s, tuple(t["concept"]), k, exp)
        else:
            hs = [h for h, c in v["helpers"].items() if c == t["concept"]]
            ok = all(R.concept_check(cid, s, h, k, exp)[0] for h in hs)
        assert ok, f"{cid} fails {t['kind']} at n = {k}"


def test_proposer_is_independent_of_every_candidate() -> None:
    """The simulated proposer reads the words in Python; it must agree with the human reference
    on 0..N (a sanity check on the oracle, not on any candidate)."""
    for cj in CONJS:
        tab = RESULTS[cj]["candidates"]["human-ref"]["table"]
        assert tab == [R.ORACLE[cj](n) for n in range(len(tab))]
