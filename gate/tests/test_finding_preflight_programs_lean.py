"""F13-T23, lean tier: the text the service sends the hosted checker for its new refusals means
what the fast tier reads it as, on the pinned toolchain.

The fast tier (``api/tests/test_finding_preflight_refusals.py``) fakes the checker, so it cannot
see a Lean error in the program or a line number in the wrong place. Here each composed text is
run through the real ``lean`` at 4.33.1 and read back with the service's own readers:

* the witness program's ``axioms`` (audit Q-b): a witness that uses a Context declaration, which
  is restated with ``sorry``, rests on ``sorryAx``; a closed one does not;
* the statement part (audit Q-a): an error in the statement lies on the lines
  ``checks.statement_lines`` names, and an error in the witness does not;
* the relation program (audit Q-c): the gate's ``expectedRelationType`` asked through the
  service's text agrees with the label's direction, reads ``relation``'s axioms, and a broken
  relation proof's error lies on the relation proof's own lines; with the root restated in the
  Context (a declared dep) the text declares it once and still elaborates.

Core Lean only, so the program's own elaboration is what is under test, not Mathlib's.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from opn_api import checks
from opn_gate.toolchain import ResolvedToolchain

pytestmark = pytest.mark.lean

CONTEXT = (
    "-- inlined by the network from Nodes.«n».Context (F13-R5)\n"
    "theorem Opn.dep : ∀ n : Nat, n + 0 = n := by\n  sorry\n"
)
STATEMENT = "theorem Opn.s : (∀ n : Nat, n + 0 = n) → True := by\n  sorry\n"
BROKEN_STATEMENT = "theorem Opn.s : (∀ n : Nat, n + 0 = Nat.nope n) → True := by\n  sorry\n"
CLOSED = "theorem witness : ∀ n : Nat, n + 0 = n := fun _ => rfl\n"
THROUGH_CONTEXT = "theorem witness : ∀ n : Nat, n + 0 = n := Opn.dep\n"
BROKEN_WITNESS = "theorem witness : ∀ n : Nat, n + 0 = n := fun _ => rfl rfl\n"

VARIANT = "theorem Opn.v : ∀ n : Nat, n + 0 = n := by\n  sorry\n"
ROOT = "theorem Opn.r : ∀ n : Nat, 0 + n = n := by\n  sorry\n"
#: partial: the root implies the variant.
PARTIAL = (
    "-- relation: partial\n"
    "theorem relation : (∀ n : Nat, 0 + n = n) → (∀ n : Nat, n + 0 = n) :=\n"
    "  fun _ _ => rfl\n"
)
#: resolves: the variant implies the root; given as the partial label's direction, it is wrong.
RESOLVES = (
    "-- relation: resolves\n"
    "theorem relation : (∀ n : Nat, n + 0 = n) → (∀ n : Nat, 0 + n = n) :=\n"
    "  fun _ n => Nat.zero_add n\n"
)
SORRY_RELATION = (
    "-- relation: partial\n"
    "theorem relation : (∀ n : Nat, 0 + n = n) → (∀ n : Nat, n + 0 = n) := by\n  sorry\n"
)
BROKEN_RELATION = (
    "-- relation: partial\n"
    "theorem relation : (∀ n : Nat, 0 + n = n) → (∀ n : Nat, n + 0 = n) :=\n"
    "  fun _ _ => rfl rfl\n"
)


def lean(pinned: ResolvedToolchain, tmp_path: Path, text: str) -> dict[str, Any]:
    """The text through the pinned ``lean``, as a body in the checker's shape: ``okay``, and
    Lean's messages split into errors and infos, each ``<file>:<line>:<col>: …`` as Lean prints
    them (the checker's file is ``-``; ``checks.error_line`` reads either)."""
    source = tmp_path / "Preflight.lean"
    source.write_text(text, encoding="utf-8")
    exe = pinned.libdir.parent.parent / "bin" / "lean"
    proc = subprocess.run(
        [str(exe), str(source)], capture_output=True, text=True, check=False, timeout=600
    )
    messages: list[str] = []
    for line in proc.stdout.splitlines():
        if line.startswith(str(source) + ":"):
            messages.append(line)
        elif messages:
            messages[-1] += "\n" + line
    # 4.33 prints a named error as ``error(lean.unknownIdentifier):``, an unnamed one ``error:``;
    # the checker sorts by severity, so only the position is read from the text.
    errors = [m for m in messages if re.search(r": error[(:]", m.split("\n", 1)[0])]
    infos = proc.stdout.splitlines()  # lean prints an info message bare, as the preview test reads
    return {
        "okay": not errors,
        "lean_messages": {"errors": errors, "warnings": [], "infos": infos},
        "stdout": proc.stdout,
    }


# --- Q-b: the witness's axioms


def test_a_witness_through_a_context_declaration_rests_on_sorry(
    pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    formal = CONTEXT + "\n" + STATEMENT
    body = lean(pinned, tmp_path, checks.witness_text(formal, THROUGH_CONTEXT, "Opn.s"))
    assert body["okay"], body["stdout"]
    assert checks.witness_verdict(body) == {
        "expected": "∀ (n : Nat), n + (0 : Nat) = n",
        "given": "∀ (n : Nat), n + (0 : Nat) = n",
        "matches": True,
    }, body["stdout"]
    axioms = checks.witness_axioms(body)
    assert axioms is not None and checks.SORRY_AXIOM in axioms, body["stdout"]

    body = lean(pinned, tmp_path, checks.witness_text(formal, CLOSED, "Opn.s"))
    assert body["okay"], body["stdout"]
    assert checks.witness_axioms(body) == [], body["stdout"]


# --- Q-a: the statement part


def test_a_statement_error_lies_on_the_statement_lines(
    pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    formal = CONTEXT + "\n" + BROKEN_STATEMENT
    body = lean(pinned, tmp_path, checks.witness_text(formal, CLOSED, "Opn.s"))
    assert not body["okay"], body["stdout"]
    lines = checks.statement_lines(formal)
    on_statement = checks.errors_on_lines(body, 1, lines)
    assert on_statement, body["stdout"]
    assert all("Nat.nope" in e for e in on_statement), on_statement


def test_a_witness_error_does_not(pinned: ResolvedToolchain, tmp_path: Path) -> None:
    formal = CONTEXT + "\n" + STATEMENT
    body = lean(pinned, tmp_path, checks.witness_text(formal, BROKEN_WITNESS, "Opn.s"))
    assert not body["okay"], body["stdout"]
    assert checks.lean_errors(body), body["stdout"]
    assert checks.errors_on_lines(body, 1, checks.statement_lines(formal)) == [], body["stdout"]


# --- Q-c: the relation program


def relation(
    pinned: ResolvedToolchain, tmp_path: Path, proof: str, label: str, **kw: Any
) -> tuple[checks.RelationText, dict[str, Any]]:
    formal = kw.get("formal", VARIANT)
    root = kw.get("root", ROOT)
    composed = checks.relation_text(
        formal, root, proof, variant_decl="Opn.v", root_decl="Opn.r", label=label
    )
    return composed, lean(pinned, tmp_path, composed.text)


def test_the_right_direction_matches(pinned: ResolvedToolchain, tmp_path: Path) -> None:
    _, body = relation(pinned, tmp_path, PARTIAL, "partial")
    assert body["okay"], body["stdout"]
    found = checks.relation_verdict(body)
    assert found is not None, body["stdout"]
    assert found["matches"] is True
    assert checks.SORRY_AXIOM not in found["axioms"]
    _, body = relation(pinned, tmp_path, RESOLVES, "resolves")
    assert body["okay"], body["stdout"]
    assert (checks.relation_verdict(body) or {}).get("matches") is True, body["stdout"]


def test_the_wrong_direction_does_not(pinned: ResolvedToolchain, tmp_path: Path) -> None:
    _, body = relation(pinned, tmp_path, RESOLVES.replace("resolves", "partial"), "partial")
    assert body["okay"], body["stdout"]
    found = checks.relation_verdict(body)
    assert found is not None and found["matches"] is False, body["stdout"]
    assert found["expected"] != found["declared"]


def test_a_sorry_relation_rests_on_sorry(pinned: ResolvedToolchain, tmp_path: Path) -> None:
    _, body = relation(pinned, tmp_path, SORRY_RELATION, "partial")
    assert body["okay"], body["stdout"]  # a sorry is a warning
    found = checks.relation_verdict(body)
    assert found is not None and checks.SORRY_AXIOM in found["axioms"], body["stdout"]


def test_a_broken_relation_errs_on_its_own_lines(pinned: ResolvedToolchain, tmp_path: Path) -> None:
    composed, body = relation(pinned, tmp_path, BROKEN_RELATION, "partial")
    assert not body["okay"], body["stdout"]
    own = checks.errors_on_lines(body, composed.root_end + 1, composed.relation_end)
    assert own, body["stdout"]
    assert checks.errors_on_lines(body, 1, composed.root_end) == [], body["stdout"]


def test_a_root_in_the_context_is_declared_once(pinned: ResolvedToolchain, tmp_path: Path) -> None:
    """The variant declares the root as a dep: its Context (inlined into ``formal``) restates the
    root's theorem, and the root block is left out."""
    formal = "-- inlined by the network from Nodes.«v».Context (F13-R5)\n" + ROOT + "\n" + VARIANT
    composed, body = relation(pinned, tmp_path, PARTIAL, "partial", formal=formal, root=None)
    assert composed.text.count("theorem Opn.r ") == 1
    assert body["okay"], body["stdout"]
    assert (checks.relation_verdict(body) or {}).get("matches") is True, body["stdout"]
