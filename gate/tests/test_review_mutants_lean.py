"""F26-T7: the mutation stage held to the first prototype's counts (R8; AC6; lean tier).

The prototype (``engineering/prototypes/formalization-round``, evidence in
``engineering/evidence/v3.36-prototype/``) mutated each conjecture's human reference and caught
every mutant that changes the meaning: 5 of Goldbach's 9, 13 of Legendre's 15 and 15 of
Oppermann's 19, the rest proved equivalent (2, Goldbach) or not elaborating (2, 2, 4). Here the job
runs on the same reference, in core Lean under the pinned toolchain, with the intent tests the
prototype ended with on record (its proposer's seeds and every answered question, cited as the
simulated proposer's: ``fixtures/review/prototype.json``). Each mutant the prototype ran is found
by its claim's text and must end the same way; the two D-11 classes the prototype did not run
(``hypothesis``, ``quantifier``) are on top, and none of them may survive the tests either.

With only the proposer's seeds on record the tests are weaker, and the mutants they cannot tell
from the reference survive: each becomes a question (R8), as the prototype's "would raise a
question" did.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from review_support import DATE, PROTOTYPE, add_test_record, make_graph, prototype_lean
from test_review_mutants import claim_of, prototype_ops

from opn_gate import review_job, review_lean, review_mutants
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

CITED = "the first prototype's simulated proposer (engineering/evidence/v3.36-prototype)"
#: The prototype's results, as this job's exhibit results.
AS_OURS = {"caught": "fail", "equivalent": "proved", "does not elaborate": "error"}
EXPECTED = {
    "goldbach": {"total": 9, "fail": 5, "proved": 2, "error": 2},
    "legendre": {"total": 15, "fail": 13, "proved": 0, "error": 2},
    "oppermann": {"total": 19, "fail": 15, "proved": 0, "error": 4},
}


def review_of(
    conj: str, tmp: Path, real: LocalToolchain, pinned: ResolvedToolchain, *, seeds_only: bool
) -> tuple[Path, dict[str, Any]]:
    graph, _ids = make_graph(
        tmp,
        target=conj,
        words=PROTOTYPE[conj]["words"],
        candidates={"human-ref": prototype_lean(conj, "human-ref")},
        people=("human-ref",),
    )
    for t in PROTOTYPE[conj]["tests"]:
        if seeds_only and t["origin"] != "proposer's seed":
            continue
        case = review_lean.Case(
            t["probe"], t["n"], tuple(t["set"]) if t["set"] else None, t["concept"]
        )
        add_test_record(graph, conj, case, bool(t["expected"]), "citation", CITED)
    spec = json.loads((graph / "targets" / conj / "gate-spec.json").read_text())
    runner = review_lean.Runner(real, pinned, tmp / "work", budget_s=120, jobs=4)
    settings = review_job.Settings(date=DATE, budget_s=120, jobs=4)
    return graph, review_job.review_run(graph, conj, runner, spec, settings)


@pytest.mark.parametrize("conj", ["goldbach", "legendre", "oppermann"])
def test_ac6_every_meaning_changing_mutant_is_caught(
    conj: str, real_toolchain: LocalToolchain, pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    _graph, summary = review_of(conj, tmp_path, real_toolchain, pinned, seeds_only=False)
    m = summary["mutants"]
    assert m, summary
    theirs = {claim_of(x["claim"]): AS_OURS[x["result"]] for x in PROTOTYPE[conj]["mutants"]}
    rep = review_lean.prepare("c-00000000", prototype_lean(conj, "human-ref"), ["prime"])
    assert isinstance(rep, review_lean.Cand)
    found, _ = review_mutants.mutants(rep, ["prime"])
    classes = {mu.label: mu for mu in found}
    ours_proto: dict[str, str] = {}
    extra: list[dict[str, Any]] = []
    for r in m["results"]:
        if prototype_ops(classes[r["label"]]):
            ours_proto[r["claim"]] = r["result"]
        else:
            extra.append(r)
    assert ours_proto == theirs, {"ours": ours_proto, "theirs": theirs}
    counts = {k: sum(1 for v in ours_proto.values() if v == k) for k in ("fail", "proved", "error")}
    assert {"total": len(ours_proto), **counts} == EXPECTED[conj]
    # the classes the prototype did not run: none survives the tests
    assert [r for r in extra if r["result"] == "pass"] == [], extra
    assert m["survived"] == 0 and m["capped"] is False


def test_ac6_a_mutant_the_seeds_cannot_tell_apart_becomes_a_question(
    real_toolchain: LocalToolchain, pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    graph, summary = review_of("legendre", tmp_path, real_toolchain, pinned, seeds_only=True)
    m = summary["mutants"]
    survived = [r for r in m["results"] if r["result"] == "pass"]
    assert survived, m
    qdir = graph / "targets" / "legendre" / "review" / "questions"
    asked = [yaml.safe_load(p.read_text()) for p in sorted(qdir.glob("*.yaml"))]
    refs = {q["raised_by"]["ref"] for q in asked if q["raised_by"]["kind"] == "mutant"}
    # every surviving mutant raised a question, or shares its case with one that did
    assert refs and refs <= {r["exhibit"] for r in survived}
    assert all(q["question"].endswith("?") and "claim" not in q["question"] for q in asked)
    # each survivor the prototype ran is one it caught only by a question's answer
    theirs = {claim_of(x["claim"]) for x in PROTOTYPE["legendre"]["mutants"]}
    assert {r["claim"] for r in survived if r["claim"] in theirs}
