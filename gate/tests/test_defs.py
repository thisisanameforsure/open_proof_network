"""F11-T3: a target's definitions in the build (``opn_gate.defs``; F11-R2, R7; F01-Q2).

No graph had a ``defs/`` before F11, so nothing staged one: a node importing ``Defs.X`` failed
step 4 with an unknown module. These are the rules of the staging — order by imports, the
refusals, and that every compiler of a Context builds the definitions first — over the fake
seam; the real elaboration of the on-ramp definitions is the lean and docker tiers' business.
"""

from __future__ import annotations

from pathlib import Path

from fakes import FakeToolchain, witness_result
from harness import TARGET, copy_graph, make_context

from opn_gate import admit, defs, pipeline
from opn_gate.diagnostic import Diagnostic
from opn_gate.toolchain import ElabResult

DIVIDES = (
    "/-! Divisibility, written out (F11-T1). -/\n\n"
    "def Opn.Divides (a b : Nat) : Prop := ∃ c : Nat, b = a * c\n"
)
PRIME = (
    "import Defs.Divides\n\n"
    "def Opn.IsPrime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d : Nat, Opn.Divides d p → d = 1 ∨ d = p\n"  # noqa: RUF001
)
FACT = (
    "import Mathlib.Tactic\n\n"
    "def Opn.fact : Nat → Nat\n  | 0 => 1\n  | n + 1 => (n + 1) * Opn.fact n\n"
)


def target_with(tmp_path: Path, files: dict[str, str]) -> Path:
    root = copy_graph(tmp_path)
    target = root / "targets" / TARGET
    (target / "defs").mkdir(exist_ok=True)
    for p in (target / "defs").iterdir():
        if p.is_file():
            p.unlink()
    for name, text in files.items():
        (target / "defs" / name).write_text(text, encoding="utf-8")
    return target


def test_order_follows_imports_not_names(tmp_path: Path) -> None:
    """``IsPrime`` imports ``Divides`` and sorts before it alphabetically; the build order puts
    the import first. A file with no ``Defs`` import keeps its alphabetical place."""
    target = target_with(
        tmp_path, {"IsPrime.lean": PRIME, "Divides.lean": DIVIDES, "Fact.lean": FACT}
    )
    ordered = defs.order(target)
    assert not isinstance(ordered, Diagnostic)
    assert [d.module for d in ordered] == ["Defs.Divides", "Defs.Fact", "Defs.IsPrime"]
    assert all(d.source.parent == target / "defs" for d in ordered)


def test_no_defs_directory_is_no_definitions(tmp_path: Path) -> None:
    root = copy_graph(tmp_path)
    target = root / "targets" / TARGET
    (target / "defs" / ".gitkeep").unlink(missing_ok=True)
    (target / "defs").rmdir()
    assert defs.order(target) == []
    assert (
        defs.compile_all(FakeToolchain(), FakeToolchain().resolved, target, tmp_path / "w") is None
    )


def test_refusals_are_named(tmp_path: Path) -> None:
    """A cycle, a file that is not a module name, an import of a definition the target does not
    have, and an import of another node: each refused before anything is staged."""
    cyc_a = "import Defs.B\ndef Opn.a : Nat := 1\n"
    cyc_b = "import Defs.A\ndef Opn.b : Nat := 2\n"
    problem = defs.order(target_with(tmp_path / "1", {"A.lean": cyc_a, "B.lean": cyc_b}))
    assert isinstance(problem, Diagnostic) and problem.code == "defs-cycle"
    assert problem.details["cycle"] == ["A", "B", "A"]

    problem = defs.order(target_with(tmp_path / "2", {"my-defs.lean": DIVIDES}))
    assert isinstance(problem, Diagnostic) and problem.code == "defs-name"
    assert problem.details["file"] == "my-defs.lean"

    problem = defs.order(target_with(tmp_path / "3", {"IsPrime.lean": PRIME}))
    assert isinstance(problem, Diagnostic) and problem.code == "defs-import"
    assert problem.details["module"] == "Defs.Divides"

    node_import = "import Nodes.«tutorial-and-swap».Statement\ndef Opn.x : Nat := 0\n"
    problem = defs.order(target_with(tmp_path / "4", {"X.lean": node_import}))
    assert isinstance(problem, Diagnostic) and problem.code == "defs-import"
    assert "library modules and other definitions only" in problem.message
    assert not (tmp_path / "4" / "graph" / "work").exists()


def test_stage_copies_in_order_and_compile_is_idempotent(tmp_path: Path) -> None:
    """Staged under ``<src>/Defs/`` in build order; compiled once per work directory — the
    second caller sharing it (admission's statement check after step 1, say) recompiles nothing."""
    target = target_with(tmp_path, {"IsPrime.lean": PRIME, "Divides.lean": DIVIDES})
    fake = FakeToolchain()
    work = tmp_path / "work"
    assert defs.compile_all(fake, fake.resolved, target, work) is None
    assert (work / "src" / "Defs" / "Divides.lean").read_text() == DIVIDES
    assert [c for c in fake.calls if c.startswith("elaborate:")] == [
        "elaborate:Defs.Divides",
        "elaborate:Defs.IsPrime",
    ]
    assert defs.compile_all(fake, fake.resolved, target, work) is None
    assert len([c for c in fake.calls if c.startswith("elaborate:")]) == 2
    assert len([c for c in fake.calls if c.startswith("elaborate:")]) == 2


def test_a_definition_that_does_not_elaborate_is_named(tmp_path: Path) -> None:
    target = target_with(tmp_path, {"IsPrime.lean": PRIME, "Divides.lean": DIVIDES})
    fake = FakeToolchain(elab=ElabResult(ok=False))
    problem = defs.compile_all(fake, fake.resolved, target, tmp_path / "work")
    assert problem is not None and problem.code == "defs-elaboration"
    assert problem.details["module"] == "Defs.Divides" and problem.details["file"] == "Divides.lean"
    # The first failure is the answer: nothing after it is attempted.
    assert [c for c in fake.calls if c.startswith("elaborate:")] == ["elaborate:Defs.Divides"]


def test_the_pipeline_builds_the_definitions_before_any_node(tmp_path: Path) -> None:
    """Step 4 compiles ``Defs.*`` first, so a Context or Proof importing one resolves."""
    ctx = make_context(tmp_path, node_id="and-swap-reassoc")
    target_with(tmp_path / "unused", {})  # keep the helper honest about an empty defs/
    target = ctx.graph_root / "targets" / TARGET
    (target / "defs" / "Divides.lean").write_text(DIVIDES, encoding="utf-8")
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step is None, verdict.as_dict()
    elaborated = [c for c in ctx.toolchain.calls if c.startswith("elaborate:")]  # type: ignore[attr-defined]
    assert elaborated[0] == "elaborate:Defs.Divides"
    assert all(not c.startswith("elaborate:Defs.") for c in elaborated[1:])


def test_admission_builds_the_definitions_before_the_context(tmp_path: Path) -> None:
    """The statement check (admission's ``layout``) compiles the definitions first, and a
    definition that does not elaborate is that check's failure, naming the file."""
    good_witness = witness_result(expected="∃ p q, p ∧ q", witness="∃ p q, p ∧ q")
    ctx = make_context(
        tmp_path, node_id="and-reassoc", toolchain=FakeToolchain(witness=good_witness)
    )
    target = ctx.graph_root / "targets" / TARGET
    (target / "defs" / "Divides.lean").write_text(DIVIDES, encoding="utf-8")
    result = admit.run(ctx)
    assert result.admitted, result.as_dict()
    elaborated = [c for c in ctx.toolchain.calls if c.startswith("elaborate:")]  # type: ignore[attr-defined]
    assert elaborated[0] == "elaborate:Defs.Divides"

    (target / "defs" / "bad name.lean").write_text("def x := 1\n", encoding="utf-8")
    result = admit.run(make_context(tmp_path / "b", node_id="and-reassoc"))
    assert result.admitted  # the copy in tmp_path/b has no such file: the fixture is untouched
    refused = admit.run(ctx)
    assert not refused.admitted and refused.first_failing_check == "layout"
    assert refused.diagnostic is not None and refused.diagnostic.code == "defs-name"
