"""F26-T4: the ported wrapper under the real toolchain (R5; lean tier, make verify-lean).

The fast tier checks the wrapper's text; this checks the claim the text makes — that the
restatement through the named predicates is the original, by ``Iff.rfl`` — with the pinned Lean.
Core only, so the laptop can run it: the statement is over ``Nat.gcd`` (a named constant, which is
what the wrapper can delegate; the brief's ``∧`` is infix notation, which it cannot, and the fast
tier pins that refusal). A wrapper whose restatement is not the original fails on its ``port``
line: that is the detector, not a review of the text.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from opn_gate import review_format
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain

pytestmark = pytest.mark.lean

ORIGINAL = (
    "/-! A core-only root: two coprime naturals are coprime the other way round. -/\n\n"
    "theorem T.gcd_symm : ∀ a b : Nat, Nat.gcd a b = 1 → Nat.gcd b a = 1 := by\n  sorry\n"
)
CONCEPTS = ["gcd"]


def elaborate(tc: LocalToolchain, pinned: ResolvedToolchain, tmp_path: Path, text: str) -> object:
    src = tmp_path / "Wrapper.lean"
    src.write_text(text, encoding="utf-8")
    return tc.elaborate(pinned, src, "Wrapper", tmp_path / "out", timeout_s=120)


def test_the_wrapper_elaborates_and_its_port_is_accepted(
    real_toolchain: LocalToolchain, pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    text = review_format.wrapper_for(ORIGINAL, CONCEPTS)
    assert "theorem port : conj ↔ original := Iff.rfl" in text
    assert review_format.returned_reason(text, CONCEPTS) is None
    elab = elaborate(real_toolchain, pinned, tmp_path, text)
    assert elab.ok, elab  # type: ignore[attr-defined]
    assert elab.errors == (), elab  # type: ignore[attr-defined]
    # no sorry survives into the wrapper: the original is carried as a Prop, not a theorem
    assert not any("sorry" in m.text for m in elab.messages), elab  # type: ignore[attr-defined]


def test_a_wrong_restatement_fails_on_the_port(
    real_toolchain: LocalToolchain, pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    text = review_format.wrapper_for(ORIGINAL, CONCEPTS)
    wrong = text.replace("IsGcd b a = 1", "IsGcd b a = 2")
    assert wrong != text
    elab = elaborate(real_toolchain, pinned, tmp_path, wrong)
    assert not elab.ok, elab  # type: ignore[attr-defined]
    port_line = text.splitlines().index("theorem port : conj ↔ original := Iff.rfl") + 1
    assert [m.line for m in elab.errors] == [port_line], elab  # type: ignore[attr-defined]
