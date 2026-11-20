"""F07-T88 (B16, 2026-11-19 run): what a witness's header must carry.

The guide said a witness keeps the statement's imports unchanged, and a witness pushed through
``POST /proposals/witness`` without the statement's ``import Nodes.«…».Context`` line merged.
Step 7 compiles the witness as a module importing the statement's own module, with the witness's
own import lines blanked (``judging.with_header``), so every import the statement has reaches
the witness through it: an import line may be left out, and one the statement does not have is
refused. These tests pin that rule, which the guide now states.
"""

from __future__ import annotations

from pathlib import Path

from fakes import FakeToolchain, witness_result
from harness import make_context, node_dir

from opn_gate import pipeline
from opn_gate.steps import default_steps
from opn_gate.steps.witness import WitnessStep

NODE = "and-swap-reassoc"  # its Statement.lean imports Nodes.«and-swap-reassoc».Context
TYPE = "∃ p q r, (p ∧ q) ∧ r"
BODY = (
    "theorem witness : ∃ p q r : Prop, (p ∧ q) ∧ r :=\n"
    "  ⟨True, True, True, ⟨trivial, trivial⟩, trivial⟩\n"
)


def verdict_with(tmp_path: Path, witness: str) -> pipeline.Verdict:
    fake = FakeToolchain(witness=witness_result(expected=TYPE, witness=TYPE))
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    statement = (node_dir(ctx) / "Statement.lean").read_text(encoding="utf-8")
    assert "import Nodes.«and-swap-reassoc».Context" in statement
    (node_dir(ctx) / "Witness.lean").write_text(witness, encoding="utf-8")
    return pipeline.run_steps(ctx, steps=[*default_steps(), WitnessStep()])


def test_a_witness_without_the_context_import_passes(tmp_path: Path) -> None:
    assert verdict_with(tmp_path, BODY).ok


def test_a_witness_with_the_statements_import_passes(tmp_path: Path) -> None:
    assert verdict_with(tmp_path, "import Nodes.«and-swap-reassoc».Context\n\n" + BODY).ok


def test_an_import_the_statement_lacks_is_refused(tmp_path: Path) -> None:
    v = verdict_with(tmp_path, "import Mathlib.Data.Nat.Basic\n\n" + BODY)
    assert v.first_failing_step == 7
    assert v.diagnostic is not None and v.diagnostic.code == "witness-elaboration"
    assert "is not among the statement's imports" in v.diagnostic.message
