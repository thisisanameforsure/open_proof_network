"""F01-T3: step 8 over the fake seam (R4-R7, R9; AC5-AC9)."""

from __future__ import annotations

import re
from pathlib import Path

from fakes import LIBRARY_CONSTANTS, FakeToolchain, metaprogram_garbage, used_constants_result
from harness import make_context, node_dir

from opn_gate import layout, pipeline
from opn_gate.steps import default_steps
from opn_gate.steps.deps import DepsStep, context_signatures, statement_signature
from opn_gate.steps.witness import WitnessStep
from opn_gate.toolchain import MetaprogramResult

ROOT = "and-swap-reassoc"
A, B = "tutorial-and-swap", "and-reassoc"
A_MOD, B_MOD = f"Nodes.«{A}».Proof", f"Nodes.«{B}».Proof"


def run_to_eight(ctx: object) -> pipeline.Verdict:
    steps = [*default_steps(), WitnessStep(), DepsStep()]
    return pipeline.run_steps(ctx, steps=steps)  # type: ignore[arg-type]


def set_deps(ctx: object, deps: list[str]) -> None:
    meta = node_dir(ctx) / "META.yaml"  # type: ignore[arg-type]
    text = meta.read_text()
    meta.write_text(re.sub(r"^deps: .*$", "deps: [" + ", ".join(deps) + "]", text, flags=re.M))


def test_undeclared_node_dependency(tmp_path: Path) -> None:
    """AC5: deps [A], constant from B → fail naming B."""
    fake = FakeToolchain(
        constants=used_constants_result(
            [*LIBRARY_CONSTANTS, ("OpnProp.and_swap", A_MOD), ("OpnProp.and_reassoc", B_MOD)]
        )
    )
    ctx = make_context(tmp_path, node_id=ROOT, toolchain=fake)
    set_deps(ctx, [A])
    # Context.lean must still match A's statement; B's signature may remain (extra is fine).
    verdict = run_to_eight(ctx)
    assert verdict.first_failing_step == 8, verdict
    d = verdict.diagnostic
    assert d is not None and d.code == "undeclared-dependency"
    assert d.details["offences"] == [
        {"constant": "OpnProp.and_reassoc", "module": B_MOD, "node": B}
    ]
    assert "and-reassoc" in d.message


def test_declared_dependencies_pass(tmp_path: Path) -> None:
    """AC6: library, defs, and node A with deps [A] → pass, no warnings."""
    fake = FakeToolchain(
        constants=used_constants_result(
            [
                *LIBRARY_CONSTANTS,
                ("Mathlib.Foo", "Mathlib.Data.Nat.Basic"),
                ("Defs.graph", "Defs.Graph"),
                ("OpnProp.and_swap", A_MOD),
                ("OpnProp.and_reassoc", B_MOD),
                ("helper", None),
            ]
        )
    )
    ctx = make_context(tmp_path, node_id=ROOT, toolchain=fake)
    verdict = run_to_eight(ctx)
    assert verdict.ok, verdict
    assert verdict.data["deps"]["warnings"] == []
    assert verdict.data["deps"]["used"] == sorted([A, B])


def test_unused_declared_dep_warns(tmp_path: Path) -> None:
    """AC7: deps [A, B], constants only from A → pass with a warning naming B."""
    fake = FakeToolchain(
        constants=used_constants_result([*LIBRARY_CONSTANTS, ("OpnProp.and_swap", A_MOD)])
    )
    ctx = make_context(tmp_path, node_id=ROOT, toolchain=fake)
    verdict = run_to_eight(ctx)
    assert verdict.ok
    assert verdict.data["deps"]["unused"] == [B]
    assert verdict.data["deps"]["warnings"] == [
        "declared dep 'and-reassoc' contributes no constant to the proof"
    ]


def test_context_signature_mismatch(tmp_path: Path) -> None:
    """AC8: Context's signature for A differs from A's Statement → fail naming A, both hashes."""
    ctx = make_context(tmp_path, node_id=ROOT)
    context = node_dir(ctx) / "Context.lean"
    context.write_text(context.read_text().replace("p ∧ q → q ∧ p", "p ∧ q → p ∧ q"))
    verdict = run_to_eight(ctx)
    assert verdict.first_failing_step == 8
    d = verdict.diagnostic
    assert d is not None and d.code == "context-signature-mismatch"
    assert d.details["dep"] == A
    assert len(d.details["context_hash"]) == 64 and len(d.details["statement_hash"]) == 64
    assert d.details["context_hash"] != d.details["statement_hash"]
    assert "graph defect" in d.message


def test_context_missing_dep_signature(tmp_path: Path) -> None:
    ctx = make_context(tmp_path, node_id=ROOT)
    (node_dir(ctx) / "Context.lean").write_text("/-! nothing declared -/\n")
    verdict = run_to_eight(ctx)
    assert verdict.first_failing_step == 8
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "context-missing-dep"


def test_metaprogram_failure_is_step_failure(tmp_path: Path) -> None:
    """AC9 (verdict half; the CLI's nonzero exit is F00's emit())."""
    ctx = make_context(
        tmp_path, node_id=ROOT, toolchain=FakeToolchain(constants=metaprogram_garbage())
    )
    verdict = run_to_eight(ctx)
    assert verdict.verdict == "fail" and verdict.first_failing_step == 8
    d = verdict.diagnostic
    assert d is not None and d.code == "metaprogram-failed"
    assert d.details["exit_code"] == 1 and "Segmentation" in d.details["output"]


def test_unknown_module_origin_fails(tmp_path: Path) -> None:
    fake = FakeToolchain(constants=used_constants_result([("mystery", "Somewhere.Else")]))
    ctx = make_context(tmp_path, node_id=ROOT, toolchain=fake)
    verdict = run_to_eight(ctx)
    assert verdict.first_failing_step == 8
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.details["offences"][0]["node"] == "?"


def test_unreadable_dependencies_fail_closed(tmp_path: Path) -> None:
    """R9, C7: a metaprogram that ran but answered `ok: false` is `deps-unreadable` with its
    error and messages — never a pass with an empty footprint."""
    bad = MetaprogramResult(
        ok=False,
        exit_code=1,
        doc={
            "ok": False,
            "error": "unknown constant OpnProp.and_swap_reassoc",
            "messages": [{"severity": "error", "line": 1, "column": 0, "text": "unknown"}],
        },
    )
    ctx = make_context(tmp_path, node_id=ROOT, toolchain=FakeToolchain(constants=bad))
    verdict = run_to_eight(ctx)
    assert verdict.first_failing_step == 8
    d = verdict.diagnostic
    assert d is not None and d.code == "deps-unreadable"
    assert d.message == "unknown constant OpnProp.and_swap_reassoc"
    assert d.details["messages"][0]["line"] == 1
    assert "deps" not in verdict.data


def test_dep_whose_statement_is_malformed_is_a_graph_defect(tmp_path: Path) -> None:
    """R6: the dep's Statement.lean must parse to compare signatures; when it does not, step 8
    names the dep rather than passing with nothing to compare against."""
    ctx = make_context(tmp_path, node_id=ROOT)
    (node_dir(ctx).parent / A / "Statement.lean").write_text(
        "theorem OpnProp.and_swap : True := sorry\ntheorem OpnProp.extra : True := sorry\n"
    )
    verdict = run_to_eight(ctx)
    assert verdict.first_failing_step == 8, verdict
    d = verdict.diagnostic
    assert d is not None and d.code == "dep-statement"
    assert d.details["dep"] == A and "found 2" in d.message


def test_context_check_takes_the_first_offending_dep(tmp_path: Path) -> None:
    """Deps are checked in declared order; the first defect is the verdict, both hashes named."""
    ctx = make_context(tmp_path, node_id=ROOT)
    (node_dir(ctx) / "Context.lean").write_text(
        "theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by\n  sorry\n"
        "theorem OpnProp.and_reassoc : ∀ p q r : Prop, r ∧ (p ∧ q) → p ∧ (q ∧ r) := by\n  sorry\n"
    )
    verdict = run_to_eight(ctx)
    assert verdict.first_failing_step == 8
    d = verdict.diagnostic
    assert d is not None and d.code == "context-signature-mismatch" and d.details["dep"] == B


def test_constants_from_the_node_itself_and_the_submission_are_free(tmp_path: Path) -> None:
    """R4: a proof may lean on its own module and on helpers it declares (module None)."""
    fake = FakeToolchain(
        constants=used_constants_result(
            [
                *LIBRARY_CONSTANTS,
                ("OpnProp.and_swap_reassoc.aux", f"Nodes.«{ROOT}».Proof"),
                ("local_helper", None),
                ("Std.Thing", "Std.Data.HashMap"),
                ("Aesop.Thing", "Aesop.Main"),
            ]
        )
    )
    ctx = make_context(tmp_path, node_id=ROOT, toolchain=fake)
    verdict = run_to_eight(ctx)
    assert verdict.ok, verdict
    assert verdict.data["deps"]["used"] == []
    assert sorted(verdict.data["deps"]["unused"]) == sorted([A, B])


def test_tutorial_node_has_no_deps_and_passes(tmp_path: Path) -> None:
    verdict = run_to_eight(make_context(tmp_path))
    assert verdict.ok and verdict.data["deps"] == {
        "declared": [],
        "used": [],
        "unused": [],
        "warnings": [],
    }


def test_signature_helpers() -> None:
    st = layout.parse_statement(
        "import X\n\ntheorem OpnProp.and_swap : ∀ p q : Prop,\n    p ∧ q → q ∧ p := by\n  sorry\n"
    )
    assert isinstance(st, layout.Statement)
    assert statement_signature(st) == "theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p"
    sigs = context_signatures(
        "/-! deps -/\ntheorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by\n  sorry\n\n"
        "theorem OpnProp.and_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) := by\n  sorry\n"
    )
    assert sigs["OpnProp.and_swap"] == statement_signature(st)
    assert set(sigs) == {"OpnProp.and_swap", "OpnProp.and_reassoc"}
