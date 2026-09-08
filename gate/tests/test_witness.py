"""F01-T2: step 7 over the fake seam (R2, R3, R9; AC1-AC4)."""

from __future__ import annotations

from pathlib import Path

from fakes import FakeToolchain, metaprogram_garbage, witness_result
from harness import make_context, node_dir

from opn_gate import pipeline
from opn_gate.steps import default_steps
from opn_gate.steps.witness import WitnessStep
from opn_gate.toolchain import MetaprogramResult


def run_to_seven(ctx: object) -> pipeline.Verdict:
    steps = [*default_steps(), WitnessStep()]
    return pipeline.run_steps(ctx, steps=steps)  # type: ignore[arg-type]


def test_missing_witness(tmp_path: Path) -> None:
    """AC1."""
    ctx = make_context(tmp_path)
    (node_dir(ctx) / "Witness.lean").unlink()
    ctx.changes = None
    verdict = run_to_seven(ctx)
    # Layout (step 2) already requires Witness.lean; step 7 guards it again for direct callers.
    assert verdict.first_failing_step == 2
    step = WitnessStep()
    ctx2 = make_context(tmp_path / "b")
    pipeline.run_steps(ctx2)  # steps 1-5 fill the context
    (node_dir(ctx2) / "Witness.lean").unlink()
    result = step.run(ctx2)
    assert not result.ok and result.diagnostic is not None
    assert result.diagnostic.code == "witness-missing"


def test_witness_sorry(tmp_path: Path) -> None:
    """AC2."""
    fake = FakeToolchain(
        witness=witness_result(expected="∃ p q, p ∧ q", witness="∃ p q, p ∧ q", axioms=("sorryAx",))
    )
    verdict = run_to_seven(make_context(tmp_path, toolchain=fake))
    assert verdict.first_failing_step == 7
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "witness-sorry"


def test_witness_type_mismatch(tmp_path: Path) -> None:
    """AC3: both types named."""
    fake = FakeToolchain(witness=witness_result(expected="∃ p q, p ∧ q", witness="∃ p, p"))
    verdict = run_to_seven(make_context(tmp_path, toolchain=fake))
    assert verdict.first_failing_step == 7
    d = verdict.diagnostic
    assert d is not None and d.code == "witness-type-mismatch"
    assert d.details == {"expected": "∃ p q, p ∧ q", "witness": "∃ p, p"}
    assert "∃ p q, p ∧ q" in d.message and "∃ p, p" in d.message


def test_no_hypotheses_true_witness(tmp_path: Path) -> None:
    """AC4."""
    fake = FakeToolchain(witness=witness_result(expected="True", witness="True"))
    verdict = run_to_seven(make_context(tmp_path, toolchain=fake))
    assert verdict.ok
    assert verdict.data["witness"] == {"expected": "True", "witness": "True", "axioms": []}
    assert any(c.startswith("witness_type:OpnProp.and_swap:True") for c in fake.calls)


def test_witness_passes_with_allowed_axioms(tmp_path: Path) -> None:
    fake = FakeToolchain(
        witness=witness_result(
            expected="∃ p q, p ∧ q", witness="∃ p q, p ∧ q", axioms=("propext", "Classical.choice")
        )
    )
    assert run_to_seven(make_context(tmp_path, toolchain=fake)).ok


def test_witness_extra_axiom_fails(tmp_path: Path) -> None:
    fake = FakeToolchain(
        witness=witness_result(
            expected="∃ p q, p ∧ q", witness="∃ p q, p ∧ q", axioms=("opn_oracle",)
        )
    )
    verdict = run_to_seven(make_context(tmp_path, toolchain=fake))
    assert verdict.first_failing_step == 7
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "witness-axiom"


def test_witness_elaboration_error_and_shape(tmp_path: Path) -> None:
    bad = MetaprogramResult(
        ok=False,
        exit_code=1,
        doc={
            "ok": False,
            "error": "witness does not elaborate",
            "messages": [
                {"severity": "error", "line": 3, "column": 1, "text": "unknown identifier"}
            ],
        },
    )
    verdict = run_to_seven(make_context(tmp_path, toolchain=FakeToolchain(witness=bad)))
    assert verdict.first_failing_step == 7
    d = verdict.diagnostic
    assert d is not None and d.code == "witness-elaboration"
    assert d.details["messages"][0]["line"] == 3

    shape = MetaprogramResult(
        ok=False,
        exit_code=1,
        doc={
            "ok": False,
            "error": "Witness.lean must declare exactly one declaration named `witness`",
        },
    )
    verdict = run_to_seven(make_context(tmp_path / "b", toolchain=FakeToolchain(witness=shape)))
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "witness-shape"


def test_metaprogram_garbage_is_step_failure(tmp_path: Path) -> None:
    """R9."""
    verdict = run_to_seven(
        make_context(tmp_path, toolchain=FakeToolchain(witness=metaprogram_garbage()))
    )
    assert verdict.first_failing_step == 7
    d = verdict.diagnostic
    assert d is not None and d.code == "metaprogram-failed"
    assert d.details["exit_code"] == 1 and "Segmentation" in d.details["output"]
