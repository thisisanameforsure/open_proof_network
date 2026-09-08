"""F00-T5: the runner and steps 1, 4, 5 over the fake seam (R4, R5, R6, R7, R18; AC10-14)."""

from __future__ import annotations

from pathlib import Path

from fakes import FakeToolchain, witness_result
from harness import TUTORIAL, changes_against_fixture, make_context, node_dir

from opn_gate import pipeline
from opn_gate.steps import default_steps
from opn_gate.steps.base import RunContext, StepResult
from opn_gate.toolchain import AxiomResult, ElabResult, Message, ReplayResult


def test_fixture_tutorial_passes_all_four_steps(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    verdict = pipeline.run_steps(ctx)
    assert verdict.verdict == "pass"
    assert [(s.step, s.result) for s in verdict.steps] == [
        (1, "pass"),
        (2, "pass"),
        (4, "pass"),
        (5, "pass"),
        (7, "pass"),
        (8, "pass"),
    ]
    assert verdict.first_failing_step is None and verdict.diagnostic is None
    assert verdict.data["toolchain"].name == "leanprover/lean4:v4.33.1"


def test_submitted_manifest_ignored(tmp_path: Path) -> None:
    """AC10: a shipped lake-manifest.json / lean-toolchain never reaches step 1."""
    fake = FakeToolchain()
    ctx = make_context(tmp_path, toolchain=fake)
    (ctx.graph_root / "lake-manifest.json").write_text('{"packages": [{"name": "evil"}]}')
    (ctx.graph_root / "lean-toolchain").write_text("leanprover/lean4:v4.0.0\n")
    (node_dir(ctx) / "lean-toolchain").write_text("leanprover/lean4:v4.0.0\n")
    verdict = pipeline.run_steps(ctx, steps=[s for s in default_steps() if s.number == 1])
    assert verdict.ok
    assert fake.calls == ["resolve:leanprover/lean4:v4.33.1:install=False"]

    # And as a submission, those files are a step-2 rejection (the diff names them).
    ctx.changes = changes_against_fixture(ctx)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "path-forbidden"
    assert "lake-manifest.json" in verdict.diagnostic.details["paths"]


def test_first_failure_stops_pipeline(tmp_path: Path) -> None:
    """AC11."""
    fake = FakeToolchain(replay=ReplayResult(ok=False, output="kernel: declaration has metavars"))
    ctx = make_context(tmp_path, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.verdict == "fail"
    assert verdict.first_failing_step == 4
    assert [(s.step, s.result) for s in verdict.steps] == [
        (1, "pass"),
        (2, "pass"),
        (4, "fail"),
        (5, "skipped"),
        (7, "skipped"),
        (8, "skipped"),
    ]
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "kernel-replay-failed"
    assert "metavars" in verdict.diagnostic.details["output"]
    assert not any(c.startswith("axioms:") for c in fake.calls)


def test_elaboration_failure_is_step4_with_messages(tmp_path: Path) -> None:
    msg = Message("Proof.lean", 4, 8, "error", "type mismatch")
    fake = FakeToolchain(elab=ElabResult(ok=False, messages=(msg,)))
    ctx = make_context(tmp_path, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "elaboration-failed"
    assert verdict.diagnostic.details["messages"][0]["line"] == 4


def test_axiom_outside_allowlist(tmp_path: Path) -> None:
    """AC12."""
    fake = FakeToolchain(
        axiom_result=AxiomResult(ok=True, axioms=frozenset({"propext", "sorryAx"}))
    )
    ctx = make_context(tmp_path, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 5
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "axiom-not-allowed"
    assert verdict.diagnostic.details["axioms"] == ["sorryAx"]
    assert "sorryAx" in verdict.diagnostic.message


def test_native_decide_rejected(tmp_path: Path) -> None:
    """AC13."""
    axioms = frozenset({"OpnProp.and_swap._native.native_decide.ax_1_1"})
    fake = FakeToolchain(axiom_result=AxiomResult(ok=True, axioms=axioms))
    ctx = make_context(tmp_path, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 5
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "native-decide"


def test_allowed_axioms_pass(tmp_path: Path) -> None:
    fake = FakeToolchain(
        axiom_result=AxiomResult(ok=True, axioms=frozenset({"propext", "Classical.choice"}))
    )
    assert pipeline.run_steps(make_context(tmp_path, toolchain=fake)).ok


def test_unexpected_error_is_a_failure(tmp_path: Path) -> None:
    """AC14 (the nonzero exit is the CLI's job, T6; here: the verdict records the exception)."""
    fake = FakeToolchain(raise_on="kernel_replay")
    ctx = make_context(tmp_path, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.verdict == "fail"
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "unexpected-error"
    assert verdict.diagnostic.details["exception"] == "RuntimeError"
    assert "blew up" in verdict.diagnostic.message


def test_missing_toolchain_is_step1_failure(tmp_path: Path) -> None:
    ctx = make_context(tmp_path, toolchain=FakeToolchain(missing=True))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 1
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "toolchain-missing"


def test_mathlib_graph_fails_step1_visibly(tmp_path: Path) -> None:
    ctx = make_context(tmp_path, spec_overrides={"mathlib_sha": "f" * 40})
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 1
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "mathlib-unsupported"


def test_step2_failures_from_content(tmp_path: Path) -> None:
    ctx = make_context(tmp_path)
    proof = node_dir(ctx) / "Proof.lean"
    proof.write_text(proof.read_text().replace("and_swap", "and_swap_renamed"))
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "proof-not-statement"

    ctx = make_context(tmp_path / "b", node_id="and-reassoc")
    (node_dir(ctx) / "Proof.lean").unlink()
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "proof-missing"

    ctx = make_context(tmp_path / "c")
    (node_dir(ctx) / "stray.lean").write_text("")
    ctx.changes = None
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "layout-extra"


def test_steps_run_in_d4_order_regardless_of_list_order(tmp_path: Path) -> None:
    class Marker:
        number = 9
        name = "marker"

        def run(self, ctx: RunContext) -> StepResult:
            ctx.data["marker"] = True
            return StepResult.passed()

    steps = [Marker(), *reversed(default_steps())]
    verdict = pipeline.run_steps(make_context(tmp_path), steps=steps)
    assert [s.step for s in verdict.steps] == [1, 2, 4, 5, 7, 8, 9]
    assert verdict.data["marker"] is True


def test_verdict_as_dict_truncates_long_diagnostics(tmp_path: Path) -> None:
    fake = FakeToolchain(replay=ReplayResult(ok=False, output="x" * 20_000))
    verdict = pipeline.run_steps(make_context(tmp_path, toolchain=fake))
    doc = verdict.as_dict(max_bytes=8192)
    assert doc["diagnostic"]["truncated"] is True
    assert len(str(doc["diagnostic"])) < 9000
    assert doc["steps"][2]["diagnostic"]["truncated"] is True
    assert TUTORIAL  # the fixture node under test


def test_step_order_7_before_8(tmp_path: Path) -> None:
    """F01-AC10: 1-5 pass, 7 fails, 8 does not run."""
    fake = FakeToolchain(witness=witness_result(expected="∃ p q, p ∧ q", witness="True"))
    verdict = pipeline.run_steps(make_context(tmp_path, toolchain=fake))
    assert verdict.first_failing_step == 7
    assert [(s.step, s.result) for s in verdict.steps][-2:] == [(7, "fail"), (8, "skipped")]
    assert not any(c.startswith("used_constants") for c in fake.calls)


def test_root_node_stages_dependency_closure(tmp_path: Path) -> None:
    """F01-Q4: deps are built first with generated Contexts; the node's Context imports them."""
    fake = FakeToolchain()
    ctx = make_context(tmp_path, node_id="and-swap-reassoc", toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict
    staged = verdict.data["staged"]
    assert staged.order == ("tutorial-and-swap", "and-reassoc", "and-swap-reassoc")
    ctx_text = (staged.node_dir("and-swap-reassoc") / "Context.lean").read_text()
    assert "import Nodes.«tutorial-and-swap».Proof" in ctx_text
    assert "import Nodes.«and-reassoc».Proof" in ctx_text
    elaborated = [c for c in fake.calls if c.startswith("elaborate:")]
    assert elaborated[0] == "elaborate:Nodes.«tutorial-and-swap».Context"
    assert elaborated[-1] == "elaborate:Nodes.«and-swap-reassoc».Proof"
    assert (staged.build / "Nodes" / "and-reassoc" / "Proof.olean").exists()
    assert any(c.startswith("kernel_replay:Nodes.«and-swap-reassoc».Proof") for c in fake.calls)


def test_unproved_dep_blocks_at_step4(tmp_path: Path) -> None:
    ctx = make_context(tmp_path, node_id="and-swap-reassoc")
    (node_dir(ctx).parent / "and-reassoc" / "Proof.lean").unlink()
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "dep-unproved"
    assert verdict.diagnostic.details["dep"] == "and-reassoc"
