"""F06-T9 (Q14): a partial's precheck answer names each hole with the statement it will become.

The finding (2026-09-24, the erdos-1050 HTTP tester, `engineering/evidence/testers-2026-09-24/
erdos-1050-http.md`, bug 5): "Precheck names holes but not their derived statements". Before
submitting a skeleton the tester could not see whether ``clear hden`` had kept hole ``hrem`` from
inheriting ``hden`` as a hypothesis: the precheck result's step 4 diagnostic carries the hole
*names* only (``artifact-partial``, details ``holes=[...]``), while the extractor's full report,
each hole's ``closed_type`` and the witness type step 7 will ask of it, sat in ``ctx.data`` and
was read only by the post-merge job, after the merge. The same report now rides in the result
beside ``steps``: like ``steps`` it is outside the signed attestation, which it does not change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from precheck import job as precheck_job

from opn_gate import pipeline

HOLE = {
    "name": "hrem",
    "type": "0 < e n",
    "closed_type": "∀ (n : Nat), 1 ≤ n → 0 < e n",
    "defeq_goal": False,
    "defeq_sibling": None,
    "defeq_ancestor": None,
    "closed_roundtrip": True,
    "expected_witness": "∃ (n : Nat), 1 ≤ n",
}
JOB = {"id": "01JOB", "node_id": "erdos-1050--h1-v2", "bundle_digest": "a" * 64}


@dataclass
class Settings:
    diagnostic_max_bytes: int = 16_384


@dataclass
class Ctx:
    data: dict[str, Any] = field(default_factory=dict)
    settings: Settings = field(default_factory=Settings)


def verdict(ok: bool = True) -> pipeline.Verdict:
    step = pipeline.StepRecord(step=4, name="artifact", result="pass" if ok else "fail")
    return pipeline.Verdict(
        verdict="pass" if ok else "fail", steps=(step,), first_failing_step=None if ok else 4
    )


def result_of(ctx: Ctx, v: pipeline.Verdict) -> dict[str, Any]:
    build = getattr(precheck_job, "result_document", None)
    assert build is not None, "the job has no pure result builder to carry the holes"
    return dict(build(JOB, v, ctx, {"schema": "attestation/v5"}))


def partial(*holes: dict[str, Any]) -> Ctx:
    return Ctx(data={"artifact": {"kind": "partial", "holes": list(holes)}})


def test_a_partial_precheck_names_each_hole_with_its_statement_and_witness_type() -> None:
    out = result_of(
        partial(HOLE, {**HOLE, "name": "hden", "closed_type": "∀ (n : Nat), W n ≠ 0"}), verdict()
    )
    assert out["holes"] == [
        {
            "name": "hrem",
            "closed_type": "∀ (n : Nat), 1 ≤ n → 0 < e n",
            "expected_witness": "∃ (n : Nat), 1 ≤ n",
            "restates": None,
        },
        {
            "name": "hden",
            "closed_type": "∀ (n : Nat), W n ≠ 0",
            "expected_witness": "∃ (n : Nat), 1 ≤ n",
            "restates": None,
        },
    ]


def test_a_hole_that_restates_a_node_says_which() -> None:
    out = result_of(partial({**HOLE, "defeq_sibling": "erdos-1050--h1-v2--h2"}), verdict())
    assert out["holes"][0]["restates"] == "erdos-1050--h1-v2--h2"


def test_a_reduction_names_its_new_node_too() -> None:
    ctx = Ctx(data={"artifact": {"kind": "reduction", "holes": [HOLE]}})
    assert [h["name"] for h in result_of(ctx, verdict())["holes"]] == ["hrem"]


def test_a_proof_precheck_has_no_holes_key() -> None:
    assert "holes" not in result_of(
        Ctx(data={"artifact": {"kind": "proof", "holes": []}}), verdict()
    )


def test_a_precheck_that_failed_before_step_4_has_no_holes_key() -> None:
    assert "holes" not in result_of(Ctx(), verdict(ok=False))


def test_the_rest_of_the_result_is_unchanged() -> None:
    out = result_of(partial(HOLE), verdict())
    assert {k: out[k] for k in ("job_id", "node_id", "bundle_digest", "verdict")} == {
        "job_id": "01JOB",
        "node_id": "erdos-1050--h1-v2",
        "bundle_digest": "a" * 64,
        "verdict": "pass",
    }
    assert out["attestation"] == {"schema": "attestation/v5"}
    assert out["steps"][0]["step"] == 4
