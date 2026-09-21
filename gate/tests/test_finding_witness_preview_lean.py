"""F13-T14, lean tier: the text the service composes for ``mode: "witness"`` elaborates on the
pinned toolchain, and its one line agrees with step 7's own tool.

The fast tier (``api/tests/test_check_witness_mode.py``) pins what is sent and how the answer is
read. Whether what is sent *means* anything is Lean's to say: the gate's ``WitnessType.lean``
pasted after a statement and a witness, a ``run_meta`` block, a JSON line. Core Lean only, on the
shape the testers met: a hypothesis, then more binders behind it (``P → ∀ N k, C``), which the
guide's rule did not cover.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from opn_api import checks
from opn_gate.toolchain import ResolvedToolchain

pytestmark = pytest.mark.lean

STATEMENT = (
    "theorem hole : (∀ n : Nat, n + 0 = n) → ∀ (N k : Nat), ∃ m : Nat, (m : Int) = (N : Int) + k"
    " := by\n  sorry\n"
)
RIGHT = "theorem witness : ∃ (N : Nat) (k : Nat), ∀ n : Nat, n + 0 = n := ⟨0, 0, fun _ => rfl⟩\n"
WRONG = "theorem witness : ∀ n : Nat, n + 0 = n := fun _ => rfl\n"
EXPECTED = "∃ (N : Nat), ∃ (k : Nat), ∀ (n : Nat), n + (0 : Nat) = n"


def run(pinned: ResolvedToolchain, tmp_path: Path, witness: str) -> dict[str, object]:
    text = checks.witness_text(STATEMENT, witness, "hole")
    source = tmp_path / "Preview.lean"
    source.write_text(text, encoding="utf-8")
    lean = pinned.libdir.parent.parent / "bin" / "lean"
    proc = subprocess.run(
        [str(lean), str(source)], capture_output=True, text=True, check=False, timeout=600
    )
    assert ": error:" not in proc.stdout, proc.stdout
    # The service reads the line out of the checker's info messages; here they are lean's stdout.
    verdict = checks.witness_verdict({"lean_messages": {"infos": proc.stdout.splitlines()}})
    assert verdict is not None, proc.stdout
    return verdict


def test_the_preview_says_the_type_step_7_wants(pinned: ResolvedToolchain, tmp_path: Path) -> None:
    assert run(pinned, tmp_path, RIGHT) == {
        "expected": EXPECTED,
        "given": EXPECTED,
        "matches": True,
    }
    wrong = run(pinned, tmp_path, WRONG)
    assert wrong["expected"] == EXPECTED and wrong["matches"] is False
    assert run(pinned, tmp_path, "") == {"expected": EXPECTED, "given": None, "matches": None}


def test_the_expected_type_reads_back_as_a_witness_type(
    pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    """The point of printing under the round-trip options: the text can be pasted as the type of
    the contributor's own witness, and the gate's tool then calls it a match."""
    pasted = f"theorem witness : {EXPECTED} := ⟨0, 0, fun _ => rfl⟩\n"
    assert run(pinned, tmp_path, pasted)["matches"] is True
    assert json.dumps(EXPECTED)  # plain text, nothing the JSON line cannot carry
