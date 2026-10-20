# ruff: noqa: RUF001 — the fixtures are Lean source, with its double-struck letters
"""F01-T7: a dep whose statement carries ``let x :=`` in its type (testers 2026-10-15c).

Step 8's Context reader cut each signature at the first ``:=`` in the file, so a ``let`` inside
the type ended it early and a byte-identical Context read as ``context-signature-mismatch``: the
live ``erdos-1094--h2--h2--h2--h3--h1--h1--h1`` (658 of 1897 characters) stopped every proof that
depends on it. The signature ends where the Statement's does, at the ``:= sorry`` body.
"""

from __future__ import annotations

from pathlib import Path

from opn_gate import layout
from opn_gate.steps.deps import check_context, context_signatures, statement_signature

DEP = "let-dep"
PARENT = "let-parent"
DECL = "let_dep"

DEP_STATEMENT = f"""import Mathlib

/-! Hole `core` of a merged partial proof, as a node. -/

theorem {DECL} : ∀ (r : ℕ),
  (2 : ℕ) ≤ r →
    ∀ (W : ℝ), (1 : ℝ) ≤ W →
      let X :=
        (W ^ (2 : ℕ)) ^ ((2 : ℝ) * (↑r : ℝ))⁻¹;
      (0 : ℝ) ≤ X + (2 : ℝ) * (↑r : ℝ) := by
  sorry
"""


def context_text(signature_block: str) -> str:
    return f"""import Mathlib

/-! Declared dependencies (D-4 step 8): `{DEP}`. -/

open scoped Nat

{signature_block}"""


def dep_block(statement: str) -> str:
    return statement[statement.index(f"theorem {DECL}") :]


def make_nodes(tmp_path: Path, context: str) -> layout.Node:
    nodes = tmp_path / "nodes"
    (nodes / DEP).mkdir(parents=True)
    (nodes / DEP / "Statement.lean").write_text(DEP_STATEMENT, encoding="utf-8")
    parent = nodes / PARENT
    parent.mkdir()
    (parent / "Context.lean").write_text(context, encoding="utf-8")
    statement = layout.parse_statement("theorem let_parent : True := by\n  sorry\n")
    assert isinstance(statement, layout.Statement)
    return layout.Node(PARENT, "t", parent, {"deps": [DEP]}, statement)


def test_context_signature_reads_past_a_let() -> None:
    """The Context reader returns the whole signature, up to the body, not up to the `let`."""
    statement = layout.parse_statement(DEP_STATEMENT)
    assert isinstance(statement, layout.Statement)
    present = context_signatures(context_text(dep_block(DEP_STATEMENT)))
    assert present[DECL] == statement_signature(statement)


def test_identical_context_with_a_let_passes(tmp_path: Path) -> None:
    """A Context that restates the dep byte for byte is not a graph defect."""
    node = make_nodes(tmp_path, context_text(dep_block(DEP_STATEMENT)))
    assert check_context(node, [DEP]) is None


def test_a_change_inside_the_let_still_fails(tmp_path: Path) -> None:
    """Guard: the part after `let X :=` is compared too, so a stale Context there is caught."""
    stale = dep_block(DEP_STATEMENT).replace("(2 : ℝ) * (↑r : ℝ))⁻¹", "(3 : ℝ) * (↑r : ℝ))⁻¹")
    node = make_nodes(tmp_path, context_text(stale))
    problem = check_context(node, [DEP])
    assert problem is not None and problem.diagnostic is not None
    assert problem.diagnostic.code == "context-signature-mismatch"
