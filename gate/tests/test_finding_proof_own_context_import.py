"""F00-T?: a proof may add one import, its own node's Context (testers 2026-09-21, finding 2).

A merged skeleton's holes reach their parent through the parent's ``Context.lean``, which the
post-merge job rewrites with each hole's signature. A proof names them only if its header
imports that module, and a proof's header is the statement's (F00-R19). Every statement the
network writes since 2026-09-20 carries the line (F08-T13, F07-T23); the ones before it do not,
and a statement is immutable (D-3). On the live graph nine of ten nodes with holes could not be
closed through them, the roots of ``erdos-1050``, ``erdos-69`` and ``erdos-402`` among them, and
two agents spent a session on holes that could not finish their target.

Mike's ruling (2026-09-21): the gate allows that one line and nothing else. No record is
rewritten; the statement and its hash are untouched; one commit reverts it.

The acceptance tests were seen red first; the refusal tests were written with them and were
green before the rule existed, so the rule cannot be loosened past them
(``engineering/evidence/F00/``).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import GRAPH, TARGET, make_context, node_dir

from opn_gate import layout, paths, pipeline, schemas
from opn_gate.diagnostic import Diagnostic
from opn_gate.steps import RunContext

NODE = "and-swap-reassoc"  # the fixture node with two proved dependencies
OWN = f"import {layout.node_module(NODE, 'Context')}"

#: The live shape (erdos-402's root): a licence comment, the library import, a module doc, an
#: ``open``, and no own-Context import.
OLD_STATEMENT = (
    "/-\nA statement written before 2026-09-20.\n-/\n"
    "\n"
    "import Init\n"
    "\n"
    "/-! Restated by hand. -/\n"
    "\n"
    "open Nat\n"
    "\n"
    "theorem OpnProp.and_swap_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p) := by\n"
    "  sorry\n"
)
BODY = (
    " by\n  intro p q r h\n"
    "  have h2 := OpnProp.and_reassoc p q r h\n"
    "  exact ⟨h2.2.2, OpnProp.and_swap p q h.1⟩\n"
)


def parsed(text: str) -> layout.Statement:
    st = layout.parse_statement(text)
    assert not isinstance(st, Diagnostic), st
    return st


def proof(header_edit: tuple[str, str] | None = ("import Init\n", f"import Init\n{OWN}\n")) -> str:
    st = parsed(OLD_STATEMENT)
    text = st.prefix + BODY
    if header_edit is not None:
        old, new = header_edit
        assert text.count(old) == 1
        text = text.replace(old, new)
    return text


def check(
    text: str, *, node_id: str | None = NODE, statement: str = OLD_STATEMENT
) -> Diagnostic | None:
    return paths.check_proof_is_statement(parsed(statement), text, node_id=node_id)


# --- the rule: accepted --------------------------------------------------------------------------


def test_a_proof_may_add_its_own_context_import_after_the_statements_last_import() -> None:
    assert check(proof()) is None


def test_a_statement_with_no_import_takes_the_line_first() -> None:
    bare = "theorem OpnProp.and_swap_reassoc : True := by\n  sorry\n"
    st = parsed(bare)
    assert check(f"{OWN}\n\n" + st.prefix + " trivial\n", statement=bare) is None


def test_the_unchanged_header_is_still_a_proof() -> None:
    assert check(proof(None)) is None


# --- the rule: everything else is still refused --------------------------------------------------

REFUSED = {
    "another node's Context": (
        "import Init\n",
        "import Init\nimport Nodes.«and-reassoc».Context\n",
    ),
    "its own Witness module": ("import Init\n", f"import Init\nimport Nodes.«{NODE}».Witness\n"),
    "a second added import": ("import Init\n", f"import Init\n{OWN}\nimport Std\n"),
    "a library import": ("import Init\n", "import Init\nimport Std\n"),
    "the line before the statement's imports": ("import Init\n", f"{OWN}\nimport Init\n"),
    "the line twice": ("import Init\n", f"import Init\n{OWN}\n{OWN}\n"),
    "the line after the open": ("open Nat\n", f"open Nat\n{OWN}\n"),
    "the line and a changed signature": (
        "open Nat\n\ntheorem OpnProp.and_swap_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r",
        f"{OWN}\nopen Nat\n\ntheorem OpnProp.and_swap_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ q",
    ),
    "the line and a helper": ("open Nat\n", "open Nat\ntheorem helper : True := trivial\n"),
}


@pytest.mark.parametrize("what", sorted(REFUSED))
def test_any_other_header_is_still_not_the_statement(what: str) -> None:
    d = check(proof(REFUSED[what]))
    assert d is not None and d.code == "proof-not-statement", what


def test_a_statement_that_has_the_line_takes_no_second_one() -> None:
    new = OLD_STATEMENT.replace("import Init\n", f"import Init\n{OWN}\n")
    st = parsed(new)
    assert check(st.prefix + BODY, statement=new) is None
    doubled = (st.prefix + BODY).replace(f"{OWN}\n", f"{OWN}\n{OWN}\n")
    d = check(doubled, statement=new)
    assert d is not None and d.code == "proof-not-statement"


def test_a_caller_that_names_no_node_gets_the_old_rule() -> None:
    d = check(proof(), node_id=None)
    assert d is not None and d.code == "proof-not-statement"


# --- the pipeline: a parent of the live shape closes through its dependencies -------------------


def old_shape(tmp_path: Path, proof_text: str) -> RunContext:
    """The fixture node rewritten to the live shape: its statement loses the import (and its
    META the old hash), its Proof.lean is the submission."""
    ctx = make_context(tmp_path, node_id=NODE)
    here = node_dir(ctx)
    (here / "Statement.lean").write_text(OLD_STATEMENT, encoding="utf-8")
    meta = (here / "META.yaml").read_text(encoding="utf-8")
    old_hash = schemas.content_hash((make_fixture_statement()).encode())
    new_hash = schemas.content_hash(OLD_STATEMENT.encode())
    assert old_hash in meta
    (here / "META.yaml").write_text(meta.replace(old_hash, new_hash), encoding="utf-8")
    (here / "Proof.lean").write_text(proof_text, encoding="utf-8")
    return ctx


def make_fixture_statement() -> str:
    return (layout.graph_nodes_dir(GRAPH, TARGET) / NODE / "Statement.lean").read_text("utf-8")


def test_step_2_takes_the_assembly_of_an_old_statement(tmp_path: Path) -> None:
    verdict = pipeline.run_steps(old_shape(tmp_path, proof()))
    assert verdict.first_failing_step != 2, verdict.diagnostic
    assert verdict.ok, verdict.diagnostic


def test_step_2_still_refuses_a_foreign_import_there(tmp_path: Path) -> None:
    verdict = pipeline.run_steps(old_shape(tmp_path, proof(REFUSED["a second added import"])))
    assert verdict.first_failing_step == 2
    assert verdict.diagnostic is not None and verdict.diagnostic.code == "proof-not-statement"
