"""F08-T27 (Q38; F18-R2): the attestation says which nodes the proof term rests on.

Step 8 reads every constant of the proof term with its module and so knows which declared
dependencies (and which declared uses) the proof actually draws on. Until T27 that set became
log warnings and was discarded, so a product could only follow what a node *declared*: erdos-1050's
``h1-v2`` declares four holes and its proof names one, and the problem page drew all four as the
proof. The record now keeps the set, so a closure by use follows from the attestations alone.
"""

from __future__ import annotations

import re
from pathlib import Path

from fakes import LIBRARY_CONSTANTS, FakeToolchain, used_constants_result
from harness import make_context, node_dir

from opn_gate import attestation, pipeline, schemas
from opn_gate.steps import default_steps
from opn_gate.steps.deps import DepsStep
from opn_gate.steps.witness import WitnessStep
from opn_gate.toolchain import AxiomResult

ROOT = "and-swap-reassoc"
A, B = "tutorial-and-swap", "and-reassoc"
A_MOD, B_MOD = f"Nodes.«{A}».Proof", f"Nodes.«{B}».Proof"


def run_to_eight(ctx: object) -> pipeline.Verdict:
    steps = [*default_steps(), WitnessStep(), DepsStep()]
    return pipeline.run_steps(ctx, steps=steps)  # type: ignore[arg-type]


def attest(ctx: object, verdict: pipeline.Verdict) -> dict[str, object]:
    return attestation.build(ctx, verdict, graph_commit="1" * 40)  # type: ignore[arg-type]


def test_a_proof_that_uses_one_of_two_declared_deps_records_the_one(tmp_path: Path) -> None:
    """The erdos-1050 shape in miniature: two declared, one used — the record names the one."""
    fake = FakeToolchain(
        constants=used_constants_result([*LIBRARY_CONSTANTS, ("OpnProp.and_swap", A_MOD)])
    )
    ctx = make_context(tmp_path, node_id=ROOT, toolchain=fake)
    verdict = run_to_eight(ctx)
    assert verdict.ok, verdict
    doc = attest(ctx, verdict)
    assert schemas.violations(doc) == []
    assert doc.get("footprint") == {"nodes": [A]}


def test_a_proof_that_uses_both_records_both_sorted(tmp_path: Path) -> None:
    fake = FakeToolchain(
        constants=used_constants_result(
            [*LIBRARY_CONSTANTS, ("OpnProp.and_reassoc", B_MOD), ("OpnProp.and_swap", A_MOD)]
        )
    )
    ctx = make_context(tmp_path, node_id=ROOT, toolchain=fake)
    verdict = run_to_eight(ctx)
    assert verdict.ok, verdict
    assert attest(ctx, verdict).get("footprint") == {"nodes": sorted([A, B])}


def test_a_proof_with_no_dependencies_records_an_empty_footprint(tmp_path: Path) -> None:
    """Measured and empty is a fact; it is not the same as not measured."""
    ctx = make_context(tmp_path)  # the tutorial node: no deps, library constants only
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict
    assert attest(ctx, verdict).get("footprint") == {"nodes": []}


def test_a_run_that_never_reached_step_eight_records_no_footprint(tmp_path: Path) -> None:
    """Not measured is ``None``, never an empty set (C7: a missing measurement is not zero)."""
    fake = FakeToolchain(axiom_result=AxiomResult(ok=True, axioms=frozenset({"sorryAx"})))
    ctx = make_context(tmp_path, node_id=ROOT, toolchain=fake)
    verdict = run_to_eight(ctx)
    assert verdict.first_failing_step == 5, verdict
    doc = attest(ctx, verdict)
    assert "footprint" in doc and doc["footprint"] is None


def test_a_refused_footprint_is_not_recorded_as_the_proofs(tmp_path: Path) -> None:
    """An undeclared dependency fails step 8: the attestation is a failure's, and a closure
    must never follow a set the gate refused."""
    fake = FakeToolchain(
        constants=used_constants_result(
            [*LIBRARY_CONSTANTS, ("OpnProp.and_swap", A_MOD), ("OpnProp.and_reassoc", B_MOD)]
        )
    )
    ctx = make_context(tmp_path, node_id=ROOT, toolchain=fake)
    meta = node_dir(ctx) / "META.yaml"
    meta.write_text(re.sub(r"^deps: .*$", f"deps: [{A}]", meta.read_text(), flags=re.M))
    verdict = run_to_eight(ctx)
    assert verdict.first_failing_step == 8
    assert attest(ctx, verdict)["footprint"] is None


def test_the_record_is_the_next_attestation_version_and_the_gate_still_reads_the_old() -> None:
    assert attestation.SCHEMA == "attestation/v7"  # v7: F25-T1 (automation); v6 was this task's
    assert "attestation/v5" in attestation.ACCEPTED_SCHEMAS
    assert "attestation/v6" in attestation.ACCEPTED_SCHEMAS
    assert "attestation/v7" in attestation.ACCEPTED_SCHEMAS
