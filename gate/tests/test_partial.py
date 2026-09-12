"""F11-T4 / F07-R5, R4 dispatched: a partial proof through the pipeline (D-12 #5).

F07-T2 built the artifact rule as functions and left it undispatched ("belongs with T4", which
never got a caller — F07-Q17). The on-ramp graph is seeded by a skeleton submitted as a partial
(F11-R8), so the dispatch lands here: step 2 recognises one new assembly under ``attempts/`` when
the node has no ``Proof.lean``, step 4 stages it as the proof, replays it, and ends with D-12's
judgment — the holes, the offload rule — and step 5 accepts ``sorryAx`` through those holes and
nowhere else. Over the fake seam; the real elaboration is ``test_onramp_lean.py``'s.
"""

from __future__ import annotations

from pathlib import Path

from fakes import FakeToolchain, artifact_result, witness_result
from harness import TARGET, make_context, node_dir

from opn_gate import pipeline
from opn_gate.paths import Change
from opn_gate.steps.artifact import ARTIFACT_KEY, PARTIAL_KEY

ROOT = "and-swap-reassoc"  # the fixture's unproved root: no Proof.lean
BODY = """  intro p q r h
  have right : r := sorry
  have left : q ∧ p := sorry
  exact ⟨right, left⟩
"""


def assembly_for(ctx) -> str:  # type: ignore[no-untyped-def]
    """The root's Statement.lean with its sorry replaced by an assembly with two holes — the
    shape F00-R19 demands of a proof, and R5 of a partial: header and signature verbatim."""
    statement = (node_dir(ctx) / "Statement.lean").read_text(encoding="utf-8")
    head, _, _ = statement.partition(":= by\n  sorry")
    return head + ":= by\n" + BODY


HOLES = [("right", "∀ (p q r : Prop), (p ∧ q) ∧ r → r", False), ("left", "q ∧ p", False)]
WITNESS = witness_result(expected="∃ p q r, (p ∧ q) ∧ r", witness="∃ p q r, (p ∧ q) ∧ r")


def partial_context(tmp_path: Path, *, toolchain: FakeToolchain | None = None, diff: bool = True):  # type: ignore[no-untyped-def]
    """The root with one new assembly under attempts/, as a partial submission's diff says."""
    stamp = "20260912T120000Z-someone-partial.lean"
    changes = [Change("A", f"targets/{TARGET}/nodes/{ROOT}/attempts/{stamp}")]
    fake = toolchain or FakeToolchain(witness=WITNESS, artifact=artifact_result(holes=HOLES))
    ctx = make_context(tmp_path, node_id=ROOT, toolchain=fake, changes=changes if diff else None)
    (node_dir(ctx) / "Proof.lean").unlink(missing_ok=True)  # a partial is for an unproved node
    if not diff:
        ctx.changes = None  # the harness defaults to a proof-only diff; a bare tree has none
    attempts = node_dir(ctx) / "attempts"
    attempts.mkdir(exist_ok=True)
    (attempts / stamp).write_text(assembly_for(ctx), encoding="utf-8")
    return ctx, stamp


def test_a_partial_passes_with_its_holes_named(tmp_path: Path) -> None:
    """R5: steps 1, 2, 4 (the assembly staged and replayed as the proof), 5 (sorryAx through the
    holes), 6, 7, 8 — and step 4's record names the holes for the post-merge job."""
    ctx, stamp = partial_context(tmp_path)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    assert [(s.step, s.result) for s in verdict.steps] == [
        (1, "pass"),
        (2, "pass"),
        (4, "pass"),
        (5, "pass"),
        (6, "pass"),
        (7, "pass"),
        (8, "pass"),
    ]
    step2, step4 = verdict.steps[1], verdict.steps[2]
    assert step2.diagnostic is not None and step2.diagnostic.code == "partial-submission"
    assert step2.diagnostic.details["path"] == f"attempts/{stamp}"
    assert step4.diagnostic is not None and step4.diagnostic.code == "artifact-partial"
    assert step4.diagnostic.details["holes"] == ["right", "left"]
    assert ctx.data[PARTIAL_KEY]["path"] == f"attempts/{stamp}"
    assert ctx.data[ARTIFACT_KEY]["kind"] == "partial"
    assert [h["name"] for h in ctx.data[ARTIFACT_KEY]["holes"]] == ["right", "left"]
    # The assembly was what step 4 compiled and replayed as the node's Proof module.
    staged = ctx.workdir / "src" / "Nodes" / ROOT / "Proof.lean"
    assert staged.read_text(encoding="utf-8") == assembly_for(ctx)
    calls = ctx.toolchain.calls
    assert f"kernel_replay:Nodes.«{ROOT}».Proof" in calls
    assert any(c.startswith("artifact_type:partial:") for c in calls)


def test_a_reduction_is_a_one_hole_partial(tmp_path: Path) -> None:
    fake = FakeToolchain(witness=WITNESS, artifact=artifact_result(holes=HOLES[:1]))
    ctx, _ = partial_context(tmp_path, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    assert verdict.steps[2].diagnostic is not None
    assert verdict.steps[2].diagnostic.code == "artifact-reduction"


def test_the_offload_rule_fails_step4(tmp_path: Path) -> None:
    """D-12: an assembly that is one hole, or a hole restating the goal, is not a decomposition."""
    fake = FakeToolchain(witness=WITNESS, artifact=artifact_result(holes=[], body_is_hole=True))
    ctx, _ = partial_context(tmp_path, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "offload-whole-goal"

    restated = artifact_result(holes=[("goal", "∀ p q r, (p ∧ q) ∧ r → r ∧ (q ∧ p)", True)])
    fake = FakeToolchain(witness=WITNESS, artifact=restated)
    ctx, _ = partial_context(tmp_path / "b", toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "offload-restated-goal"

    unnamed = artifact_result(holes=HOLES, unnamed=1)
    fake = FakeToolchain(witness=WITNESS, artifact=unnamed)
    ctx, _ = partial_context(tmp_path / "c", toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "hole-unnamed"


def test_sorry_is_accepted_only_through_a_partials_holes(tmp_path: Path) -> None:
    """R5: step 5 lets a partial rest on sorryAx; a *proof* resting on it is still refused."""
    from opn_gate.toolchain import AxiomResult  # noqa: PLC0415

    sorry_axioms = AxiomResult(ok=True, axioms=frozenset({"propext", "sorryAx"}))
    fake = FakeToolchain(
        witness=WITNESS, artifact=artifact_result(holes=HOLES), axiom_result=sorry_axioms
    )
    ctx, _ = partial_context(tmp_path, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()

    proof_ctx = make_context(tmp_path / "proof", toolchain=FakeToolchain(axiom_result=sorry_axioms))
    verdict = pipeline.run_steps(proof_ctx)
    assert verdict.first_failing_step == 5
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "axiom-not-allowed"
    assert verdict.diagnostic.details["axioms"] == ["sorryAx"]


def test_the_assembly_is_the_statement_with_holes(tmp_path: Path) -> None:
    """R5: the assembly declares ``theorem <node> : S`` — F00-R19's header-and-signature rule
    applies to it exactly as to a proof, so a different theorem is refused at step 2."""
    ctx, stamp = partial_context(tmp_path)
    (node_dir(ctx) / "attempts" / stamp).write_text(
        assembly_for(ctx).replace("and_swap_reassoc", "something_else"), encoding="utf-8"
    )
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "proof-not-statement"


def test_two_assemblies_in_one_diff_are_refused(tmp_path: Path) -> None:
    ctx, stamp = partial_context(tmp_path)
    other = "20260912T130000Z-else-partial.lean"
    (node_dir(ctx) / "attempts" / other).write_text(assembly_for(ctx), encoding="utf-8")
    assert ctx.changes is not None
    ctx.changes.append(Change("A", f"targets/{TARGET}/nodes/{ROOT}/attempts/{other}"))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "partial-multiple"
    assert verdict.diagnostic.details["paths"] == [f"attempts/{stamp}", f"attempts/{other}"]


def test_without_a_diff_the_newest_assembly_is_the_submission(tmp_path: Path) -> None:
    """``reproduce`` has the merge's diff; ``pregate --no-diff`` on a checkout does not, and takes
    the newest stamped assembly — which is the one just written."""
    ctx, stamp = partial_context(tmp_path, diff=False)
    older = "20260901T000000Z-else-partial.lean"
    (node_dir(ctx) / "attempts" / older).write_text("stale\n", encoding="utf-8")
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    assert ctx.data[PARTIAL_KEY]["path"] == f"attempts/{stamp}"


def test_no_proof_and_no_assembly_is_still_proof_missing(tmp_path: Path) -> None:
    ctx = make_context(tmp_path, node_id=ROOT, changes=[])
    (node_dir(ctx) / "Proof.lean").unlink(missing_ok=True)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "proof-missing"


def test_a_counterexample_is_judged_by_the_metaprogram(tmp_path: Path) -> None:
    """R4, dispatched with the same change: a Proof.lean declaring ``<node>_refuted`` skips the
    textual rule at step 2 and has its type checked at step 4; a plain proof runs nothing beyond
    F00-R19; a declaration that is neither is refused by name at step 2."""
    ctx = make_context(tmp_path)
    proof = node_dir(ctx) / "Proof.lean"
    proof.write_text(
        proof.read_text().replace(
            "theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p",
            "theorem OpnProp.and_swap_refuted : ¬ (∀ p q : Prop, p ∧ q → q ∧ p)",
        ),
        encoding="utf-8",
    )
    fake = FakeToolchain(
        artifact=artifact_result(
            kind="counterexample", expected="¬(∀ (p q : Prop), p ∧ q → q ∧ p)", matches=True
        )
    )
    ctx.toolchain = fake
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    assert verdict.steps[1].diagnostic is not None
    assert verdict.steps[1].diagnostic.code == "counterexample-submission"
    assert verdict.steps[2].diagnostic is not None
    assert verdict.steps[2].diagnostic.code == "artifact-counterexample"
    assert any(c.startswith("artifact_type:counterexample:") for c in fake.calls)

    wrong = FakeToolchain(
        artifact=artifact_result(kind="counterexample", declared="¬ True", matches=False)
    )
    ctx.toolchain = wrong
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "artifact-type-mismatch"

    # A declaration that is neither the statement nor one of D-12's suffixes is what F00-R19
    # has always refused, in its own words.
    proof.write_text(proof.read_text().replace("and_swap_refuted", "something"), encoding="utf-8")
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "proof-not-statement"

    plain = make_context(tmp_path / "plain")
    verdict = pipeline.run_steps(plain)
    assert verdict.first_failing_step is None
    assert plain.data[ARTIFACT_KEY] == {"kind": "proof", "decl": "OpnProp.and_swap"}
    assert not any(c.startswith("artifact_type:") for c in plain.toolchain.calls)  # type: ignore[attr-defined]
