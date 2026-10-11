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
from pathlib import Path
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
    node: Any = None


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
            "proved_binders": [],
        },
        {
            "name": "hden",
            "closed_type": "∀ (n : Nat), W n ≠ 0",
            "expected_witness": "∃ (n : Nat), 1 ≤ n",
            "restates": None,
            "proved_binders": [],
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


def test_a_hole_says_which_binders_its_assembly_proved() -> None:
    """F07-T44 (D-29 v3.22): the extractor marks the binders the assembly proved and narrows
    ``expected_witness`` to the rest; the precheck says which, so a skeleton author can see
    before submitting what a witness of each hole will have to exhibit."""
    out = result_of(partial({**HOLE, "proved_binders": [1]}, HOLE), verdict())
    assert [h["proved_binders"] for h in out["holes"]] == [[1], []]


def test_a_hole_whose_witness_the_bundle_carried_says_so() -> None:
    """F07-T50 (R23, AC46; D-29 v3.24): step 7 checked the witness the bundle carried for
    ``hden``; the result names its path and hash on that hole, which is what the service reads
    before it opens a pull request for a bundle with carried witnesses. A hole that carried
    none has no such key, so a result for a partial of the old shape is what it was."""
    ctx = partial(HOLE, {**HOLE, "name": "hden"})
    plain = result_of(ctx, verdict())
    ctx.data["hole_witnesses"] = [
        {
            "hole": "hden",
            "path": "attempts/20261001T000000Z-a-partial.1.witness",
            "sha256": "b" * 64,
            "expected": "∃ (n : Nat), 1 ≤ n",
            "witness": "∃ (n : Nat), 1 ≤ n",
            "axioms": [],
        }
    ]
    out = result_of(ctx, verdict())
    assert "witness" not in out["holes"][0]
    assert out["holes"][1]["witness"] == {
        "path": "attempts/20261001T000000Z-a-partial.1.witness",
        "sha256": "b" * 64,
        "checked": True,
    }
    assert [{k: v for k, v in h.items() if k != "witness"} for h in out["holes"]] == plain["holes"]
    assert all("witness" not in h for h in plain["holes"])


@dataclass
class Node:
    """The two facts ``plan_children`` reads: the node's id and its directory."""

    node_id: str
    path: Path


def test_each_hole_names_the_node_it_is_expected_to_become(tmp_path: Path) -> None:
    """Testers 2026-10-09 (A, feature): a partial's receipt did not say which node ids its holes
    would get, so a contributor learned them by polling ``get_node`` after the merge. The result
    now names each one, by the post-merge writer's own rule (``postmerge.plan_children``): a
    later decomposition numbers its holes after the earlier ones' (R22), and a hole that
    restates an existing node is that node, not a new one."""
    nodes = tmp_path / "nodes"
    (nodes / "erdos-1094--h2").mkdir(parents=True)
    (nodes / "erdos-1094--h1").mkdir()
    (nodes / "erdos-1094--h2--h1").mkdir()  # an earlier decomposition's hole
    ctx = partial(HOLE, {**HOLE, "name": "hden"})
    ctx.node = Node("erdos-1094--h2", nodes / "erdos-1094--h2")
    out = result_of(ctx, verdict())
    assert [(h["expected_node_id"], h["expected_new"]) for h in out["holes"]] == [
        ("erdos-1094--h2--h2", True),
        ("erdos-1094--h2--h3", True),
    ]


def test_without_the_node_no_hole_names_one() -> None:
    """A result built where step 2 never found the node says nothing rather than guess."""
    out = result_of(partial(HOLE), verdict())
    assert "expected_node_id" not in out["holes"][0]
