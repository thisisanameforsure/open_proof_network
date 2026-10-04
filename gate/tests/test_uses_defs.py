"""F08-T23: a proof may use a definition of its target that its statement does not import (R16,
R17; proposed decisions v3.25; the owner's ruling of 2026-10-01, testers' item B1).

A statement is immutable and a proof's header was the statement's (F00-R19), so beneath a root
stated over Mathlib alone nothing could name a definition admitted later (F11-T13): erdos-69's
skeleton needs ``Defs.Construction`` and its root imports Mathlib only. A proof, a partial or an
alternate may now carry *use lines* directly after the statement's imports, each
``import Defs.<Name>`` for a definition already on the tree.

Two things hold the line, and both are tested here with the toolchain faked:

* step 2 takes exactly that header and no other, and each line must name a definition of the
  target that is on the tree (``uses.check``);
* step 4 compares what the artifact proved with the statement as its own header reads it
  (``steps.meaning``); the real comparison is the lean tier's (``test_uses_defs_lean.py``).

The acceptance tests were seen red first; the refusals were written with them and were green
before the rule existed, so the rule cannot be loosened past them
(``engineering/evidence/F08/task-23-red.txt``).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fakes import FakeToolchain, meaning_result, metaprogram_garbage
from harness import GRAPH, TARGET, make_context, node_dir

from opn_gate import layout, paths, pipeline, postmerge, schemas, uses
from opn_gate.diagnostic import Diagnostic
from opn_gate.paths import Change
from opn_gate.steps import RunContext, meaning
from opn_gate.steps.artifact import ALTERNATE_KEY, PARTIAL_KEY

NODE = "and-swap-reassoc"  # two proved dependencies, and a statement that imports its Context
OWN = f"import {layout.node_module(NODE, 'Context')}"
USE = "import Defs.Extra"
EXTRA = "/-! Admitted after the statement was written. -/\n\ndef Opn.extra : Nat := 0\n"

#: A statement of the live shape: a library import, a doc comment, an ``open``, no own Context.
OLD_STATEMENT = (
    "import Init\n"
    "\n"
    "/-! Restated by hand. -/\n"
    "\n"
    "open Nat\n"
    "\n"
    "theorem OpnProp.and_swap_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p) := by\n"
    "  sorry\n"
)
BODY = " by\n  intro p q r h\n  exact ⟨h.2, h.1.2, h.1.1⟩\n"


def parsed(text: str) -> layout.Statement:
    st = layout.parse_statement(text)
    assert not isinstance(st, Diagnostic), st
    return st


def proof(*edits: tuple[str, str], statement: str = OLD_STATEMENT) -> str:
    text = parsed(statement).prefix + BODY
    for old, new in edits:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return text


def check(text: str, *, statement: str = OLD_STATEMENT) -> Diagnostic | None:
    return paths.check_proof_is_statement(parsed(statement), text, node_id=NODE)


def declared(text: str, *, statement: str = OLD_STATEMENT) -> tuple[str, ...]:
    return uses.declared(parsed(statement), text, NODE).modules


# --- the header rule: accepted --------------------------------------------------------------------


def test_a_proof_may_add_a_use_line_after_the_statements_last_import() -> None:
    text = proof(("import Init\n", f"import Init\n{USE}\n"))
    assert check(text) is None
    assert declared(text) == ("Defs.Extra",)


def test_use_lines_follow_the_own_context_line_where_the_proof_adds_one() -> None:
    """F00-T10's line first, then the uses: one place for each, so a header reads one way."""
    text = proof(("import Init\n", f"import Init\n{OWN}\n{USE}\nimport Defs.Other\n"))
    assert check(text) is None
    assert declared(text) == ("Defs.Extra", "Defs.Other")


def test_use_lines_lead_the_file_of_a_statement_with_no_imports() -> None:
    statement = (GRAPH / "targets" / TARGET / "nodes" / "and-reassoc" / "Statement.lean").read_text(
        encoding="utf-8"
    )
    assert layout.imports_of(statement) == []
    st = parsed(statement)
    text = f"{USE}\n" + st.prefix + " by\n  intro p q r h\n  exact ⟨h.1.1, h.1.2, h.2⟩\n"
    assert paths.check_proof_is_statement(st, text, node_id="and-reassoc") is None
    assert uses.declared(st, text, "and-reassoc").modules == ("Defs.Extra",)


def test_a_proof_without_use_lines_declares_none() -> None:
    assert declared(proof()) == ()
    assert check(proof()) is None


# --- the header rule: still refused ---------------------------------------------------------------


@pytest.mark.parametrize(
    "edit",
    [
        ("import Init\n", f"{USE}\nimport Init\n"),  # before the statement's imports
        ("import Init\n", "import Init\n\nimport Defs.Extra\n"),  # after a blank line
        ("open Nat\n", f"open Nat\n{USE}\n"),  # below the header: Lean would refuse it too
        ("import Init\n", "import Init\nimport Mathlib.Tactic\n"),  # a library module is no use
        ("import Init\n", "import Init\nimport Defs\n"),  # not a module of defs/
        ("import Init\n", "import Init\nimport Defs.Extra.Deep\n"),  # defs/ is flat
        ("import Init\n", "import Init\nimport Nodes.«and-reassoc».Context\n"),  # another's Context
        ("import Init\n", f"import Init\n{USE}\n{OWN}\n"),  # the own Context comes first
        ("import Init\n", f"import Init\n{USE}\nopen Opn\n"),  # a use line, then a new command
        ("import Init\n", f"import Init\n{USE}\ninstance : Inhabited Nat := ⟨0⟩\n"),
    ],
)
def test_any_other_header_is_refused_as_before(edit: tuple[str, str]) -> None:
    problem = check(proof(edit))
    assert problem is not None and problem.code == "proof-not-statement", problem


def test_a_use_line_does_not_excuse_a_changed_signature() -> None:
    text = proof(
        ("import Init\n", f"import Init\n{USE}\n"),
        ("(p ∧ q) ∧ r → r ∧ (q ∧ p)", "(p ∧ q) ∧ r → r ∧ (p ∧ q)"),
    )
    problem = check(text)
    assert problem is not None and problem.code == "proof-not-statement"


def test_a_use_line_does_not_excuse_an_empty_body() -> None:
    text = parsed(OLD_STATEMENT).prefix.replace("import Init\n", f"import Init\n{USE}\n") + "\n"
    problem = check(text)
    assert problem is not None and problem.code == "proof-empty"


def test_without_the_node_named_a_use_line_is_still_read() -> None:
    """The use lines do not depend on F00-T10's allowance, which needs the node's id."""
    text = proof(("import Init\n", f"import Init\n{USE}\n"))
    assert paths.check_proof_is_statement(parsed(OLD_STATEMENT), text) is None


# --- step 2 and step 4 through the pipeline -------------------------------------------------------


def defs_dir(ctx: RunContext) -> Path:
    return layout.gate_spec_path(ctx.graph_root, TARGET).parent / "defs"


def with_use(ctx: RunContext, line: str = USE, *, admit: bool = True) -> Path:
    """Rewrite the node's merged proof with ``line`` as a use line, and (unless told not to)
    put the definition it names on the tree."""
    if admit:
        (defs_dir(ctx) / "Extra.lean").write_text(EXTRA, encoding="utf-8")
    path = node_dir(ctx) / "Proof.lean"
    text = path.read_text(encoding="utf-8")
    assert text.count(OWN + "\n") == 1
    path.write_text(text.replace(OWN + "\n", f"{OWN}\n{line}\n"), encoding="utf-8")
    return path


def test_a_proof_with_an_admitted_definition_passes_and_is_held_to_the_statements_meaning(
    tmp_path: Path,
) -> None:
    fake = FakeToolchain()
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    with_use(ctx)
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    assert verdict.data[uses.USES_KEY] == {
        "modules": ["Defs.Extra"],
        "defs": ["Defs.Extra"],
        "nodes": [],
    }
    statement = layout.node_module(NODE, "Statement")
    proof_module = layout.node_module(NODE, "Proof")
    # the statement is compiled from the node's own files, in a build of its own, and compared
    # before the replay, which sees the modules it always did
    assert f"elaborate:{statement}" in fake.calls
    assert f"statement_meaning:{proof_module}:OpnProp.and_swap_reassoc" in fake.calls
    assert fake.calls.index(f"statement_meaning:{proof_module}:OpnProp.and_swap_reassoc") < next(
        i for i, c in enumerate(fake.calls) if c.startswith("kernel_replay")
    )
    assert not list((ctx.workdir / "build").rglob("Statement.olean"))
    own = ctx.workdir / meaning.MEANING_DIR
    assert (own / "build" / "Nodes" / NODE / "Statement.olean").is_file()
    # the node's Context there is the signatures D-3 gives it, never the staged proofs
    assert (own / "src" / "Nodes" / NODE / "Context.lean").read_text(encoding="utf-8") == (
        node_dir(ctx) / "Context.lean"
    ).read_text(encoding="utf-8")
    assert "import Nodes." in (ctx.workdir / "src" / "Nodes" / NODE / "Context.lean").read_text(
        encoding="utf-8"
    )
    assert verdict.data[meaning.MEANING_KEY] == {"identical": True, "matches": True}


def test_step_8_records_which_declared_definitions_the_proof_term_uses(tmp_path: Path) -> None:
    """R18: a definition's constants are free, as they always were (F01-R4); what is recorded is
    whether a declared module contributed one. An idle module is a warning, never a refusal: a
    notation or an instance is used without leaving a constant of its own module."""
    from fakes import LIBRARY_CONSTANTS, used_constants_result  # noqa: PLC0415

    fake = FakeToolchain(
        constants=used_constants_result([*LIBRARY_CONSTANTS, ("Opn.extra", "Defs.Extra")])
    )
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    (defs_dir(ctx) / "Other.lean").write_text("def Opn.other : Nat := 1\n", encoding="utf-8")
    with_use(ctx, f"{USE}\nimport Defs.Other")
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    assert verdict.data["deps"]["uses"] == {
        "defs": ["Defs.Extra", "Defs.Other"],
        "idle": ["Defs.Other"],
        "nodes": [],
    }
    assert (
        "declared use Defs.Other contributes no constant to the proof"
        in (verdict.data["deps"]["warnings"])
    )


def test_a_proof_without_uses_records_no_uses_and_is_still_held_to_its_meaning(
    tmp_path: Path,
) -> None:
    """Restated by F08-T28 (Q36): without a declaration there is no uses record, but the
    statement's meaning is compared for every proof, not only for one that declares a use."""
    fake = FakeToolchain()
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    assert uses.USES_KEY not in verdict.data
    assert verdict.data[meaning.MEANING_KEY] == {"identical": True, "matches": True}
    assert "uses" not in verdict.data["deps"]
    assert any(c.startswith("statement_meaning") for c in fake.calls)
    assert f"elaborate:{layout.node_module(NODE, 'Statement')}" in fake.calls


def test_a_definition_that_is_not_on_the_tree_is_refused_at_step_2(tmp_path: Path) -> None:
    fake = FakeToolchain()
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    with_use(ctx, admit=False)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "use-unknown-defs"
    assert verdict.diagnostic.details["module"] == "Defs.Extra"
    assert not any(c.startswith("elaborate") for c in fake.calls)


def test_a_submission_cannot_bring_its_own_definition(tmp_path: Path) -> None:
    """The path rule is untouched: a diff that adds the defs file it uses is refused first."""
    ctx = make_context(tmp_path, node_id=NODE)
    with_use(ctx)
    ctx.changes = [
        Change("M", f"targets/{TARGET}/nodes/{NODE}/Proof.lean"),
        Change("A", f"targets/{TARGET}/defs/Extra.lean"),
    ]
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "path-forbidden"


def test_a_use_line_repeating_another_is_refused(tmp_path: Path) -> None:
    ctx = make_context(tmp_path, node_id=NODE)
    with_use(ctx, f"{USE}\n{USE}")
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "use-duplicate"


def test_a_use_line_repeating_a_statement_import_is_refused(tmp_path: Path) -> None:
    ctx = make_context(tmp_path, node_id=NODE)
    here = node_dir(ctx)
    (defs_dir(ctx) / "Extra.lean").write_text(EXTRA, encoding="utf-8")
    old = (here / "Statement.lean").read_text(encoding="utf-8")
    new = f"{USE}\n" + old
    (here / "Statement.lean").write_text(new, encoding="utf-8")
    meta = (here / "META.yaml").read_text(encoding="utf-8")
    (here / "META.yaml").write_text(
        meta.replace(schemas.content_hash(old.encode()), schemas.content_hash(new.encode("utf-8"))),
        encoding="utf-8",
    )
    proof_text = (here / "Proof.lean").read_text(encoding="utf-8")
    (here / "Proof.lean").write_text(
        f"{USE}\n" + proof_text.replace(OWN + "\n", f"{OWN}\n{USE}\n"), encoding="utf-8"
    )
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "use-duplicate"


def test_a_changed_meaning_fails_step_4_before_any_replay(tmp_path: Path) -> None:
    fake = FakeToolchain(
        meaning=meaning_result(
            expected="∀ (n : Nat), @Size.size Nat instBase n = 0",
            declared="∀ (n : Nat), @Size.size Nat instTrap n = 0",
        )
    )
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    with_use(ctx)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "statement-meaning-changed"
    assert verdict.diagnostic.details["uses"] == ["Defs.Extra"]
    assert "instTrap" in verdict.diagnostic.details["declared"]
    assert not any(c.startswith("kernel_replay") for c in fake.calls)


def test_a_local_declaration_that_differs_fails_step_4(tmp_path: Path) -> None:
    fake = FakeToolchain(meaning=meaning_result(local_mismatch=("Opn.helper",)))
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    with_use(ctx)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None
    assert verdict.diagnostic.code == "statement-meaning-changed"
    assert verdict.diagnostic.details["local_mismatch"] == ["Opn.helper"]


def test_a_guard_that_cannot_answer_fails_step_4(tmp_path: Path) -> None:
    """Fail closed (C7): no verdict from the comparison is a refusal, never a pass."""
    fake = FakeToolchain(meaning=metaprogram_garbage())
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    with_use(ctx)
    verdict = pipeline.run_steps(ctx)
    assert verdict.first_failing_step == 4
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "metaprogram-failed"


def test_an_alternate_may_declare_uses(tmp_path: Path) -> None:
    fake = FakeToolchain()
    ctx = make_context(tmp_path, node_id=NODE, toolchain=fake)
    here = node_dir(ctx)
    (defs_dir(ctx) / "Extra.lean").write_text(EXTRA, encoding="utf-8")
    text = (here / "Proof.lean").read_text(encoding="utf-8")
    rel = "attempts/20261001T000000Z-prover-alternate.lean"
    (here / rel).write_text(
        text.replace(OWN + "\n", f"{OWN}\n{USE}\n").replace("exact ⟨", "exact id ⟨"),
        encoding="utf-8",
    )
    ctx.changes = [Change("A", f"targets/{TARGET}/nodes/{NODE}/{rel}")]
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    assert verdict.data[ALTERNATE_KEY]["path"] == rel
    assert verdict.data[uses.USES_KEY]["defs"] == ["Defs.Extra"]
    assert any(c.startswith("statement_meaning") for c in fake.calls)


def partial_context(tmp_path: Path, fake: FakeToolchain) -> tuple[RunContext, str, str]:
    """``and-reassoc`` with its proof taken away and one assembly under ``attempts/`` that
    declares a use."""
    from fakes import artifact_result  # noqa: PLC0415

    fake.artifact = artifact_result(
        decl="OpnProp.and_reassoc",
        expected="∀ (p q r : Prop), (p ∧ q) ∧ r → p ∧ q ∧ r",
        holes=[("h", "p ∧ q ∧ r", False)],
    )
    ctx = make_context(tmp_path, node_id="and-reassoc", toolchain=fake)
    here = node_dir(ctx)
    (defs_dir(ctx) / "Extra.lean").write_text(EXTRA, encoding="utf-8")
    (here / "Proof.lean").unlink()
    st = parsed((here / "Statement.lean").read_text(encoding="utf-8"))
    rel = "attempts/20261001T000000Z-prover-partial.lean"
    text = (
        f"{USE}\n"
        + st.prefix
        + (" by\n  intro p q r h\n  have h : p ∧ q ∧ r := sorry\n  exact h\n")
    )
    (here / rel).write_text(text, encoding="utf-8")
    ctx.changes = [Change("A", f"targets/{TARGET}/nodes/and-reassoc/{rel}")]
    return ctx, rel, text


def test_a_partial_may_declare_uses(tmp_path: Path) -> None:
    fake = FakeToolchain()
    ctx, rel, _ = partial_context(tmp_path, fake)
    verdict = pipeline.run_steps(ctx)
    assert verdict.ok, verdict.diagnostic
    assert verdict.data[PARTIAL_KEY]["path"] == rel
    assert verdict.data[uses.USES_KEY]["defs"] == ["Defs.Extra"]
    assert any(c.startswith("statement_meaning") for c in fake.calls)


# --- the holes of a partial that declared a definition --------------------------------------------


def test_a_partials_holes_import_the_definitions_it_declared(tmp_path: Path) -> None:
    """erdos-69's case: the root imports Mathlib alone, the skeleton declares the construction,
    and its holes are stated over it. A child's statement is written under the parent's imports
    *and* the assembly's definitions, or it would not elaborate."""
    ctx, rel, text = partial_context(tmp_path, FakeToolchain())
    here = node_dir(ctx)
    hole = SimpleNamespace(
        name="h",
        closed_type="∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ q ∧ r ∧ Opn.extra = 0",
        closed_roundtrip=True,
        expected_witness=None,
        defeq_sibling=None,
        proved_binders=(),
    )
    merged = postmerge.apply_partial(
        here,
        [hole],
        partial_text=text,
        pseudonym="prover",
        stamp="20261001T000000Z",
        assembly_path=rel,
    )
    assert merged.children == ("and-reassoc--h1",)
    child = here.parent / "and-reassoc--h1"
    statement = (child / "Statement.lean").read_text(encoding="utf-8")
    assert layout.imports_of(statement) == [
        "Defs.Extra",
        layout.node_module("and-reassoc--h1", "Context"),
    ]
    assert layout.validate_node(child) == []
    # the parent is untouched where it is immutable
    assert (here / "Statement.lean").read_text(encoding="utf-8") == (
        GRAPH / "targets" / TARGET / "nodes" / "and-reassoc" / "Statement.lean"
    ).read_text(encoding="utf-8")


def test_a_partial_without_uses_writes_its_holes_as_before(tmp_path: Path) -> None:
    ctx, rel, text = partial_context(tmp_path, FakeToolchain())
    here = node_dir(ctx)
    hole = SimpleNamespace(
        name="h",
        closed_type="∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ q ∧ r",
        closed_roundtrip=True,
        expected_witness=None,
        defeq_sibling=None,
        proved_binders=(),
    )
    postmerge.apply_partial(
        here,
        [hole],
        partial_text=text.replace(f"{USE}\n", ""),
        pseudonym="prover",
        stamp="20261001T000000Z",
        assembly_path=rel,
    )
    statement = (here.parent / "and-reassoc--h1" / "Statement.lean").read_text(encoding="utf-8")
    assert layout.imports_of(statement) == [layout.node_module("and-reassoc--h1", "Context")]
