"""F26-T19, lean tier: the texts the service's pair-proof pre-flight sends the hosted checker mean
what the fast tier reads them as, on the pinned toolchain.

The fast tier (``api/tests/test_pair_proof_submissions.py``) fakes the checker. Here each text the
pre-flight composes (``opn_api.pairproofs.axiom_text`` and ``pair_proofs.guarded``) runs through
the real ``lean`` at 4.33.1 over the core-Lean Legendre fixtures, and is read back with the
service's own readers (``axioms_read``, ``judge_file``): the axiom program prints the theorem's
axioms on the nonce's line, a proof that rests on ``sorry`` reads ``sorryAx``, ``native_decide``
reads an auxiliary axiom of its own, and the guarded copy of a real proof does not elaborate.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_finding_preflight_programs_lean import lean

from opn_api import pairproofs
from opn_api.app import ApiError
from opn_gate import pair_proofs, review_lean
from opn_gate.toolchain import ResolvedToolchain

pytestmark = pytest.mark.lean

FIX = Path(__file__).parent / "fixtures" / "review" / "legendre"
A, B, Z = "c-aaaaaaaa", "c-bbbbbbbb", "c-cccccccc"
NONCE = "0123456789abcdef0123456789abcdef"
HELPER = "private theorem same (p : Nat) : C_c_aaaaaaaa_p.Prime p → C_c_bbbbbbbb_p.Prime p := id\n"
PROOF = (
    "  intro hn\n  obtain ⟨p, h1, h2, h3⟩ := h hn\n"
    "  exact ⟨p, Nat.le_of_lt h1, Nat.le_of_lt h2, same p h3⟩\n"
)


def cand(cid: str, name: str) -> review_lean.Cand:
    got = review_lean.prepare(cid, (FIX / f"{name}.lean").read_text(encoding="utf-8"), ["prime"])
    assert isinstance(got, review_lean.Cand)
    return got


def fill(tmpl: str, helpers: str, proof: str) -> str:
    return tmpl.replace(pair_proofs.HELPERS_END, helpers + pair_proofs.HELPERS_END).replace(
        pair_proofs.PLACEHOLDER, proof
    )


def test_a_real_proof_passes_and_its_guarded_copy_does_not(
    pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    a, b = cand(A, "human-ref"), cand(B, "alt-closed")
    filled = fill(pair_proofs.template(a, b, "forward"), HELPER, PROOF)
    body = lean(pinned, tmp_path, pairproofs.axiom_text(filled, "opnDirection", NONCE))
    assert body["okay"], body["stdout"]
    assert pairproofs.axioms_read(body, NONCE) == [], body["stdout"]
    assert pairproofs.axioms_read(body, "f" * 32) is None, "another nonce's line is not read"
    assert pairproofs.judge_file(body, NONCE, "local", None) == pairproofs.PREFLIGHT_PASSED

    guard = lean(pinned, tmp_path, pair_proofs.guarded(filled, a))
    assert not guard["okay"], guard["stdout"]
    assert "Unknown identifier `h`" in guard["stdout"]


def test_a_proof_resting_on_sorry_reads_sorry_ax(pinned: ResolvedToolchain, tmp_path: Path) -> None:
    """The region rule refuses the word; the axiom probe is the second line of defence, and it
    sees what text cannot (a helper's admitted goal, say). Here the proof says it outright."""
    a, b = cand(A, "human-ref"), cand(B, "alt-closed")
    filled = fill(pair_proofs.template(a, b, "forward"), "", "  exact sorry\n")
    body = lean(pinned, tmp_path, pairproofs.axiom_text(filled, "opnDirection", NONCE))
    assert pairproofs.axioms_read(body, NONCE) == ["sorryAx"], body["stdout"]
    with pytest.raises(ApiError) as caught:
        pairproofs.judge_file(body, NONCE, "local", None)
    assert caught.value.code == "pair-proof-sorry"


def test_a_refutation_at_an_instance_passes_and_native_decide_does_not(
    pinned: ResolvedToolchain, tmp_path: Path
) -> None:
    """human-ref holds at n = 1 (2 and 3 lie strictly between 1 and 4); bad-plus1 asks for a
    prime strictly between n^2 and n^2 + 1, so it fails there: the forward direction is refuted."""
    a, z = cand(A, "human-ref"), cand(Z, "bad-plus1")
    tmpl = pair_proofs.template(a, z, "forward", "refutation", 1)
    by_kernel = fill(tmpl, "", "  decide\n")
    body = lean(pinned, tmp_path, pairproofs.axiom_text(by_kernel, "opnInstance", NONCE))
    assert body["okay"], body["stdout"]
    assert pairproofs.judge_file(body, NONCE, "local", None) == pairproofs.PREFLIGHT_PASSED

    native = fill(tmpl, "", "  native_decide\n")
    body = lean(pinned, tmp_path, pairproofs.axiom_text(native, "opnInstance", NONCE))
    axioms = pairproofs.axioms_read(body, NONCE)
    # Lean 4.33.1 compiles native_decide to an auxiliary axiom of its own (measured:
    # opnInstance._native.native_decide.ax_1_1), not to Lean.ofReduceBool
    assert axioms is not None and any("native_decide" in x for x in axioms), body["stdout"]
    with pytest.raises(ApiError) as caught:
        pairproofs.judge_file(body, NONCE, "local", None)
    assert caught.value.code == "pair-proof-axiom"
