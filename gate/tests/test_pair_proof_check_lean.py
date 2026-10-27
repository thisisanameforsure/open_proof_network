"""F26-T17 (R8) under the real toolchain (lean tier): the verdict on a pair proof at Lean 4.33.1.

Core-Lean Legendre candidates (``fixtures/review/legendre``), so the laptop runs it. Each test
files one text through ``pair_proof_check.verdict`` with the real seam and the gate's own
metaprograms (``opn-axioms``, ``opn-statement-meaning``): what the fast tier's fake decides from a
text's shape, Lean decides here. The degenerate case needs a second claim that holds outright, so
it uses a candidate written for it (``TRIVIAL``) rather than a Legendre reading."""

from __future__ import annotations

from pathlib import Path

import pytest

from opn_gate import pair_proof_check, pair_proofs, review_lean
from opn_gate.toolchain import LocalToolchain, ResolvedToolchain, is_native_decide_axiom

pytestmark = pytest.mark.lean

FIX = Path(__file__).parent / "fixtures" / "review" / "legendre"
A, B = "c-aaaaaaaa", "c-bbbbbbbb"
HELPER = "private theorem same (p : Nat) : C_c_aaaaaaaa_p.Prime p → C_c_bbbbbbbb_p.Prime p := id\n"
PROOF = (
    "  intro hn\n  obtain ⟨p, h1, h2, h3⟩ := h hn\n"
    "  exact ⟨p, Nat.le_of_lt h1, Nat.le_of_lt h2, same p h3⟩\n"
)
#: A claim that holds at every n, so a direction into it is provable without its hypothesis.
TRIVIAL = (
    "def claim (n : Nat) : Prop := n = n\n"
    "instance : DecidablePred claim := fun n => by unfold claim; infer_instance\n"
)


def cand(cid: str, name: str, source: str | None = None) -> review_lean.Cand:
    text = source if source is not None else (FIX / f"{name}.lean").read_text(encoding="utf-8")
    c = review_lean.prepare(cid, text, ["prime"])
    assert isinstance(c, review_lean.Cand), c
    return c


def fill(tmpl: str, helpers: str = "", proof: str = PROOF) -> str:
    return tmpl.replace(pair_proofs.HELPERS_END, helpers + pair_proofs.HELPERS_END).replace(
        pair_proofs.PLACEHOLDER, proof
    )


@pytest.fixture
def real(
    real_toolchain: LocalToolchain, pinned: ResolvedToolchain, lean_pkg: Path
) -> tuple[LocalToolchain, ResolvedToolchain]:
    del lean_pkg  # built: the metaprograms the verdict asks
    return real_toolchain, pinned


def judge(
    real: tuple[LocalToolchain, ResolvedToolchain],
    text: str,
    tmpl: str,
    first: review_lean.Cand,
    tmp_path: Path,
    *,
    kind: pair_proofs.Kind = "proof",
) -> pair_proof_check.Verdict:
    seam, resolved = real
    return pair_proof_check.verdict(
        seam,
        resolved,
        text,
        tmpl,
        first=first,
        kind=kind,
        workdir=tmp_path / "work",
        timeout_s=300,
    )


def test_a_correct_proof_passes(
    real: tuple[LocalToolchain, ResolvedToolchain], tmp_path: Path
) -> None:
    a, b = cand(A, "human-ref"), cand(B, "alt-closed")
    tmpl = pair_proofs.template(a, b, "forward")
    got = judge(real, fill(tmpl, helpers=HELPER), tmpl, a, tmp_path)
    assert got.ok, got.as_dict()
    assert set(got.axioms) <= set(pair_proof_check.ALLOWED_AXIOMS)


def test_a_proof_that_ignores_its_hypothesis_is_refused_by_the_guard(
    real: tuple[LocalToolchain, ResolvedToolchain], tmp_path: Path
) -> None:
    a, b = cand(A, "human-ref"), cand(B, "trivial", TRIVIAL)
    tmpl = pair_proofs.template(a, b, "forward")
    got = judge(real, fill(tmpl, proof="  exact rfl\n"), tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-degenerate"), got.as_dict()


def test_a_sorry_reached_through_a_helper_is_refused(
    real: tuple[LocalToolchain, ResolvedToolchain], tmp_path: Path
) -> None:
    """``sorryAx`` named outright passes the regions' word scan (it is not the word ``sorry``),
    so Lean and the axioms judge are what refuse it."""
    a, b = cand(A, "human-ref"), cand(B, "alt-closed")
    tmpl = pair_proofs.template(a, b, "forward")
    helper = "private theorem cheat (p : Prop) : p := sorryAx p false\n"
    text = fill(tmpl, helpers=helper, proof="  exact cheat _\n")
    assert pair_proof_check.static(text, tmpl) is None  # the word scan lets it through
    got = judge(real, text, tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-sorry"), got.as_dict()


def test_the_word_sorry_in_a_helper_never_reaches_lean(
    real: tuple[LocalToolchain, ResolvedToolchain], tmp_path: Path
) -> None:
    a, b = cand(A, "human-ref"), cand(B, "alt-closed")
    tmpl = pair_proofs.template(a, b, "forward")
    text = fill(tmpl, helpers="private theorem cheat (p : Prop) : p := sorry\n")
    got = judge(real, text, tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-forbidden")
    assert not (tmp_path / "work.judge").exists()


def test_a_helper_resting_on_native_decide_is_refused_by_the_axiom_judge(
    real: tuple[LocalToolchain, ResolvedToolchain], tmp_path: Path
) -> None:
    """The helper rule allows ``native_decide`` (step 5 judges it with a waiver in a
    ``Proof.lean``); here nothing waives it, and the theorem's axioms name the compiler."""
    a, b = cand(A, "human-ref"), cand(B, "alt-closed")
    tmpl = pair_proofs.template(a, b, "forward")
    helper = HELPER + "private theorem small : 5 < 7 := by native_decide\n"
    proof = "  have _ := small\n" + PROOF
    text = fill(tmpl, helpers=helper, proof=proof)
    assert pair_proof_check.static(text, tmpl) is None
    got = judge(real, text, tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-axiom"), got.as_dict()
    assert any(is_native_decide_axiom(x) for x in got.details["axioms"]), got.details


def test_decide_native_in_the_proof_region_is_refused_by_the_axiom_judge(
    real: tuple[LocalToolchain, ResolvedToolchain], tmp_path: Path
) -> None:
    """``decide +native`` is ``native_decide`` without the word the proof region forbids."""
    a, b = cand(A, "human-ref"), cand(B, "alt-closed")
    tmpl = pair_proofs.template(a, b, "forward")
    proof = "  have _ : 5 < 7 := by decide +native\n" + PROOF
    text = fill(tmpl, helpers=HELPER, proof=proof)
    assert pair_proof_check.static(text, tmpl) is None
    got = judge(real, text, tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-axiom"), got.as_dict()


def test_a_proof_that_does_not_close_is_refused_with_lean_s_error(
    real: tuple[LocalToolchain, ResolvedToolchain], tmp_path: Path
) -> None:
    a, b = cand(A, "human-ref"), cand(B, "alt-closed")
    tmpl = pair_proofs.template(a, b, "forward")
    got = judge(real, fill(tmpl, proof="  intro hn\n  exact h hn\n"), tmpl, a, tmp_path)
    assert (got.ok, got.code) == (False, "pair-proof-elaboration"), got.as_dict()
    assert got.details["messages"]


def test_a_refutation_at_a_real_instance_passes(
    real: tuple[LocalToolchain, ResolvedToolchain], tmp_path: Path
) -> None:
    """At n = 0 the faithful reading holds (its domain is n at least 1) and ``bad-zero``, which
    dropped the domain, fails: there is no prime p with 0 < p < 1."""
    a, b = cand(A, "human-ref"), cand(B, "bad-zero")
    tmpl = pair_proofs.template(a, b, "forward", "refutation", 0)
    got = judge(real, fill(tmpl, proof="  decide\n"), tmpl, a, tmp_path, kind="refutation")
    assert got.ok, got.as_dict()


def test_a_refutation_at_an_instance_where_it_does_not_hold_is_refused(
    real: tuple[LocalToolchain, ResolvedToolchain], tmp_path: Path
) -> None:
    a, b = cand(A, "human-ref"), cand(B, "bad-zero")
    tmpl = pair_proofs.template(a, b, "forward", "refutation", 1)
    got = judge(real, fill(tmpl, proof="  decide\n"), tmpl, a, tmp_path, kind="refutation")
    assert (got.ok, got.code) == (False, "pair-proof-elaboration"), got.as_dict()
