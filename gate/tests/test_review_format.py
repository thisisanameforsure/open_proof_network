# ruff: noqa: RUF001 — the cases are Lean source, with its double-struck letters and bars
"""F26-T4: the format rule (R5; D-9 v3.39), fast tier.

A candidate names each concept the review's manifest lists as its own predicate; one that writes
a concept inline is *returned* to its author with the reason, never discarded (R4). The corpus is
the first prototype's (``engineering/prototypes/formalization-round/``, F26-Q2): its faithful
candidates meet the rule, and ``alt-inline`` — primality written out in the claim with no named
helper — is the candidate the rule exists for. A ported statement that does not meet the rule gets
a wrapper proved equal to it by ``Iff.rfl``; the fast tier checks the wrapper's text, the lean
tier (``test_review_format_lean.py``) that the toolchain accepts the proof.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from opn_gate import review_format, schemas

ROOT = Path(__file__).resolve().parents[2]
ROUND = ROOT / "engineering" / "prototypes" / "formalization-round" / "candidates"
MATHLIB = ROOT / "engineering" / "prototypes" / "formalization-review-mathlib" / "candidates"
CONCEPTS = ["Prime"]


def candidate(conjecture: str, name: str) -> str:
    return (ROUND / conjecture / f"{name}.lean").read_text(encoding="utf-8")


# -- concepts_named ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("conjecture", "name"),
    [("goldbach", "human-ref"), ("goldbach", "agent-a"), ("legendre", "agent-c")],
)
def test_the_prototypes_faithful_candidates_name_the_concept(conjecture: str, name: str) -> None:
    """``Prime`` (human-ref) and ``IsPrime`` (the agents) both count as naming ``Prime``."""
    assert review_format.concepts_named(candidate(conjecture, name), CONCEPTS) == {"Prime": True}
    assert review_format.returned_reason(candidate(conjecture, name), CONCEPTS) is None


def test_the_inline_candidate_is_returned_naming_the_concept() -> None:
    """``alt-inline`` writes ``2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0`` in the claim itself."""
    text = candidate("legendre", "alt-inline")
    assert review_format.concepts_named(text, CONCEPTS) == {"Prime": False}
    reason = review_format.returned_reason(text, CONCEPTS)
    assert reason is not None
    assert "Prime" in reason
    assert "returned" in reason


def test_the_match_is_case_insensitive_and_accepts_the_is_prefix() -> None:
    """The manifest's concepts are words (``prime``, ``divides``); a candidate's predicate may be
    ``Prime``, ``IsPrime`` or ``isPrime`` (an ``abbrev`` or a ``structure`` counts too)."""
    assert review_format.concepts_named(candidate("goldbach", "human-ref"), ["prime"]) == {
        "prime": True
    }
    assert review_format.concepts_named(candidate("goldbach", "agent-a"), ["prime"]) == {
        "prime": True
    }
    abbrev = "abbrev isPrime (p : Nat) : Prop := 2 ≤ p\ndef claim (n : Nat) : Prop := isPrime n\n"
    assert review_format.concepts_named(abbrev, ["Prime"]) == {"Prime": True}
    structure = (
        "structure Prime (p : Nat) : Prop where\n  two : 2 ≤ p\ntheorem t : Prime 2 := sorry\n"
    )
    assert review_format.concepts_named(structure, ["prime"]) == {"prime": True}


def test_a_mathlib_constant_is_not_a_local_predicate() -> None:
    """``Nat.Prime p`` in the claim names Mathlib's notion, not the candidate's own; the reason
    says so, since that is what the author has to change."""
    text = "theorem t : ∀ n : ℕ, 4 ≤ n → ∃ p, Nat.Prime p ∧ Nat.Prime (n - p) := sorry\n"
    assert review_format.concepts_named(text, CONCEPTS) == {"Prime": False}
    reason = review_format.returned_reason(text, CONCEPTS)
    assert reason is not None
    assert "Nat.Prime" in reason


def test_a_predicate_the_claim_never_uses_does_not_meet_the_rule() -> None:
    """The probes replace the predicate; a declared ``IsPrime`` the claim does not use leaves them
    nothing to replace, which is the defect the rule exists to catch."""
    text = (
        "def IsPrime (p : Nat) : Prop := 2 ≤ p\n"
        "def claim (n : Nat) : Prop := ∃ p, p ≤ n ∧ Nat.Prime p\n"
    )
    reason = review_format.returned_reason(text, CONCEPTS)
    assert reason is not None
    assert "IsPrime" in reason


def test_a_comment_does_not_name_a_concept() -> None:
    text = "-- def Prime (p : Nat) : Prop := True\ndef claim (n : Nat) : Prop := n = n\n"
    assert review_format.concepts_named(text, CONCEPTS) == {"Prime": False}


def test_every_concept_is_checked_and_the_first_missing_one_is_the_reason() -> None:
    text = candidate("goldbach", "human-ref")
    named = review_format.concepts_named(text, ["Prime", "Even"])
    assert named == {"Prime": True, "Even": False}
    reason = review_format.returned_reason(text, ["Even", "Prime"])
    assert reason is not None
    assert "Even" in reason


def test_no_concepts_means_the_rule_is_met() -> None:
    assert review_format.concepts_named(candidate("goldbach", "human-ref"), []) == {}
    assert review_format.returned_reason(candidate("goldbach", "human-ref"), []) is None


# -- the claim ------------------------------------------------------------------------------------


def test_a_candidate_with_no_conjecture_is_returned() -> None:
    """Predicates alone are not a candidate: nothing to probe, nothing to pair."""
    text = "def Prime (p : Nat) : Prop := 2 ≤ p\ninstance : DecidablePred Prime := sorry\n"
    reason = review_format.returned_reason(text, CONCEPTS)
    assert reason is not None
    assert "no conjecture" in reason
    assert review_format.returned_reason("", CONCEPTS) is not None


def test_a_candidate_with_two_theorems_is_returned() -> None:
    text = (
        "def Prime (p : Nat) : Prop := 2 ≤ p\n"
        "theorem a : Prime 2 := sorry\n"
        "theorem b : Prime 3 := sorry\n"
    )
    reason = review_format.returned_reason(text, CONCEPTS)
    assert reason is not None
    assert "2" in reason


def test_the_claim_may_be_a_theorem_or_the_prototypes_prop_def() -> None:
    """Both shapes carry the same conjecture; the rule reads either."""
    theorem = "def IsPrime (p : Nat) : Prop := 2 ≤ p\ntheorem t : ∀ n, ∃ p, IsPrime p := sorry\n"
    conj = "def IsPrime (p : Nat) : Prop := 2 ≤ p\ndef conj : Prop := ∀ n : Nat, ∃ p, IsPrime p\n"
    assert review_format.returned_reason(theorem, CONCEPTS) is None
    assert review_format.returned_reason(conj, CONCEPTS) is None


# -- wrapper_for --------------------------------------------------------------------------------


def incumbent_original(target: str) -> str:
    """The live statement the second prototype ported: the incumbent file's header and its
    ``original`` line, without the hand-written wrapper around them (the file *is* a wrapper, the
    shape ``wrapper_for`` must regenerate)."""
    lines = (MATHLIB / target / "incumbent.lean").read_text(encoding="utf-8").splitlines()
    keep = [ln for ln in lines if ln.startswith(("open ", "import ", "def original "))]
    return "\n".join(keep) + "\n"


def test_the_wrapper_for_erdos_1003_names_the_concept_and_proves_the_port_by_iff_rfl() -> None:
    """The live root reads ``Set.Infinite {n | φ n = φ (n + 1)}`` under ``open scoped Nat``; the
    wrapper names the totient and restates the claim through the name."""
    original = incumbent_original("erdos-1003")
    text = review_format.wrapper_for(original, ["totient"])
    assert review_format.concepts_named(text, ["totient"]) == {"totient": True}
    assert review_format.returned_reason(text, ["totient"]) is None
    assert "def IsTotient := Nat.totient" in text
    assert "def conj : Prop := Set.Infinite {n | IsTotient n = IsTotient (n + 1)}" in text
    assert "theorem port : conj ↔ original := Iff.rfl" in text
    # the original is carried verbatim: its text is what the wrapper is proved equal to
    assert "def original : Prop := Set.Infinite {n | φ n = φ (n + 1)}" in text
    assert text.startswith("open scoped Nat\n")


def test_the_wrapper_for_erdos_727_delegates_a_named_mathlib_constant() -> None:
    original = incumbent_original("erdos-727")
    text = review_format.wrapper_for(original, ["factorial"])
    assert "def IsFactorial := Nat.factorial" in text
    assert "Set.Infinite {n : ℕ | (IsFactorial (n + k)) ^ 2 ∣ IsFactorial (2 * n)}" in text
    assert "theorem port : conj ↔ original := Iff.rfl" in text
    assert review_format.returned_reason(text, ["factorial"]) is None


def test_the_wrapper_restates_a_theorem_shaped_statement() -> None:
    """A node's ``Statement.lean`` is a sorry-bodied theorem (F00-R19); its type is the claim."""
    original = (
        "/-! A core-only root. -/\n\n"
        "theorem T.gcd_symm : ∀ a b : Nat, Nat.gcd a b = 1 → Nat.gcd b a = 1 := by\n  sorry\n"
    )
    text = review_format.wrapper_for(original, ["gcd"])
    assert "sorry" not in text
    assert "def original : Prop := ∀ a b : Nat, Nat.gcd a b = 1 → Nat.gcd b a = 1" in text
    assert "def IsGcd := Nat.gcd" in text
    assert "def conj : Prop := ∀ a b : Nat, IsGcd a b = 1 → IsGcd b a = 1" in text
    assert "theorem port : conj ↔ original := Iff.rfl" in text


def test_the_wrapper_closes_a_theorems_binders_into_its_statement() -> None:
    original = "theorem t (a b : Nat) (h : 0 < a) : Nat.gcd a b ≤ a := sorry\n"
    text = review_format.wrapper_for(original, ["gcd"])
    assert "def original : Prop := ∀ (a b : Nat) (h : 0 < a), Nat.gcd a b ≤ a" in text


def test_a_wrapper_already_meeting_the_rule_is_refused() -> None:
    """A statement that names the concept itself needs no wrapper; writing one would double the
    predicate. The caller (T5) asks ``returned_reason`` first; the function says so too."""
    with pytest.raises(ValueError, match="already"):
        review_format.wrapper_for(candidate("goldbach", "human-ref"), CONCEPTS)


def test_a_concept_the_original_writes_by_infix_notation_cannot_be_wrapped() -> None:
    """``p ∧ q`` has no textual rewrite into ``IsAnd p q`` that keeps precedence; the wrapper
    refuses, naming the concept, rather than emit a restatement that may not be the original."""
    original = "theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by\n  sorry\n"
    with pytest.raises(ValueError, match="And"):
        review_format.wrapper_for(original, ["And"])


def test_a_concept_the_original_does_not_use_cannot_be_wrapped() -> None:
    original = "def original : Prop := ∀ n : ℕ, Nat.Prime n → 2 ≤ n\n"
    with pytest.raises(ValueError, match="divides"):
        review_format.wrapper_for(original, ["prime", "divides"])


# -- format_exhibit -----------------------------------------------------------------------------


def test_the_format_exhibit_is_a_returned_exhibit_with_no_lean_file() -> None:
    reason = review_format.returned_reason(candidate("legendre", "alt-inline"), CONCEPTS)
    assert reason is not None
    doc = review_format.format_exhibit(
        "c-0123abcd",
        reason,
        target="legendre",
        toolchain="leanprover/lean4:v4.33.1",
        mathlib_sha=None,
        run="local",
        date="2026-10-12",
    )
    assert schemas.validate(doc, "exhibit/v1") == doc
    assert doc["kind"] == "format"
    assert doc["result"] == "returned"
    assert doc["lean_file"] is None
    assert doc["test"] is None
    assert doc["candidate"] == "c-0123abcd"
    assert doc["detail"] == reason


def test_the_format_exhibits_id_is_a_function_of_the_candidate_and_the_reason() -> None:
    """R13: a second run writes nothing, so the same return has the same id; another candidate's
    or another reason's differs."""
    kw = {
        "target": "legendre",
        "toolchain": "leanprover/lean4:v4.33.1",
        "mathlib_sha": "0" * 40,
        "run": "123",
        "date": "2026-10-12",
    }
    a = review_format.format_exhibit("c-0123abcd", "Prime inline", **kw)
    b = review_format.format_exhibit("c-0123abcd", "Prime inline", **{**kw, "run": "456"})
    c = review_format.format_exhibit("c-89abcdef", "Prime inline", **kw)
    d = review_format.format_exhibit("c-0123abcd", "Even inline", **kw)
    assert a["id"] == b["id"]
    assert len({a["id"], c["id"], d["id"]}) == 3
    assert a["mathlib_sha"] == "0" * 40
