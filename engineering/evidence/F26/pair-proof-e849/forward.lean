-- opn-review: {"a": "c-ae9bea28", "b": "c-fb339e85", "case": null, "direction": "forward", "kind": "proof", "op": "pair-proof"}
import Mathlib

namespace C_c_ae9bea28_p
/-
Copyright 2025 The Formal Conjectures Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-/



/-! Erdős problem 849: Is it true that, for every integer $t\geq1$, there is some integer $a$ such that ${n \choose k} = a$ with $1\leq k \le \frac{n}{2}$ has exactly $t$ solutions? — imported from google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/849.lean at c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae, Apache-2.0); the registry states a yes/no question as `answer(sorry) ↔ P`; this states P, its affirmative reading (F11-Q24). Drafted by gate/tools/wave.py (F14-T11) and read by the curator before import (R13). -/

open Nat

def opnClaim : Prop :=
  ∀ t ≥ 1, ∃ a : ℕ,
      {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ choose n k = a}.ncard = t

end C_c_ae9bea28_p

namespace C_c_fb339e85_p
/-- Erdős 849 read literally: for every t ≥ 1 some a has exactly t solutions (n, k) of
C(n, k) = a with 1 ≤ k ≤ n/2, counted as pairs, with `encard` so an infinite solution set
is never mistaken for a finite count. -/
def opnClaim : Prop :=
  ∀ t : ℕ, 1 ≤ t → ∃ a : ℕ,
    {p : ℕ × ℕ | 1 ≤ p.2 ∧ 2 * p.2 ≤ p.1 ∧ Nat.choose p.1 p.2 = a}.encard = t

end C_c_fb339e85_p

-- opn-pair-proof: helpers begin (private theorem, lemma, def or abbrev declarations only)
private theorem step_lt (n k : ℕ) (h : 2 * (k + 1) ≤ n) : Nat.choose n k < Nat.choose n (k + 1) := by
  have e := Nat.choose_succ_right_eq n k
  have hp : 0 < Nat.choose n k := Nat.choose_pos (by omega)
  have hk : k + 1 < n - k := by omega
  by_contra hc
  push_neg at hc
  have : Nat.choose n k * (n - k) ≤ Nat.choose n k * (k + 1) := by
    calc Nat.choose n k * (n - k) = Nat.choose n (k + 1) * (k + 1) := e.symm
      _ ≤ Nat.choose n k * (k + 1) := Nat.mul_le_mul_right _ hc
  have := Nat.le_of_mul_le_mul_left this hp
  omega

private theorem mono_lt (n : ℕ) :
    ∀ j i : ℕ, i < j → 2 * j ≤ n → Nat.choose n i < Nat.choose n j := by
  intro j
  induction j with
  | zero => intro i h; omega
  | succ j ih =>
    intro i hij hj
    have hs := step_lt n j hj
    rcases Nat.lt_succ_iff_lt_or_eq.mp hij with h | h
    · exact lt_trans (ih i h (by omega)) hs
    · subst h; exact hs

private theorem row_unique (n k₁ k₂ : ℕ) (h₁ : 2 * k₁ ≤ n) (h₂ : 2 * k₂ ≤ n)
    (h : Nat.choose n k₁ = Nat.choose n k₂) : k₁ = k₂ := by
  rcases lt_trichotomy k₁ k₂ with hl | he | hg
  · have := mono_lt n k₂ k₁ hl h₂; omega
  · exact he
  · have := mono_lt n k₁ k₂ hg h₁; omega

private theorem rows_eq_pairs (a : ℕ) :
    {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ Nat.choose n k = a}.ncard =
      {p : ℕ × ℕ | 1 ≤ p.2 ∧ 2 * p.2 ≤ p.1 ∧ Nat.choose p.1 p.2 = a}.ncard := by
  have himg : (Prod.fst '' {p : ℕ × ℕ | 1 ≤ p.2 ∧ 2 * p.2 ≤ p.1 ∧ Nat.choose p.1 p.2 = a}) =
      {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ Nat.choose n k = a} := by
    ext n
    simp only [Set.mem_image, Set.mem_setOf_eq, Prod.exists]
    constructor
    · rintro ⟨m, k, ⟨hk, hkm, hc⟩, rfl⟩
      exact ⟨k, hk, hkm, hc⟩
    · rintro ⟨k, hk, hkn, hc⟩
      exact ⟨n, k, ⟨hk, hkn, hc⟩, rfl⟩
  rw [← himg]
  apply Set.ncard_image_of_injOn
  rintro ⟨n₁, k₁⟩ ⟨hk₁, hkn₁, hc₁⟩ ⟨n₂, k₂⟩ ⟨hk₂, hkn₂, hc₂⟩ hn
  simp only at hn hk₁ hkn₁ hc₁ hk₂ hkn₂ hc₂
  subst hn
  have := row_unique n₁ k₁ k₂ hkn₁ hkn₂ (hc₁.trans hc₂.symm)
  subst this
  rfl

private theorem rows_le (a : ℕ) :
    {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ Nat.choose n k = a} ⊆ Set.Icc 2 a := by
  rintro n ⟨k, hk, hkn, rfl⟩
  refine ⟨by omega, ?_⟩
  rcases Nat.lt_or_ge 1 k with h | h
  · have := mono_lt n k 1 h hkn
    rw [Nat.choose_one_right] at this
    omega
  · have : k = 1 := by omega
    subst this
    rw [Nat.choose_one_right]

private theorem pairs_finite (a : ℕ) :
    {p : ℕ × ℕ | 1 ≤ p.2 ∧ 2 * p.2 ≤ p.1 ∧ Nat.choose p.1 p.2 = a}.Finite := by
  apply (Set.finite_Icc ((0:ℕ), (0:ℕ)) (a, a)).subset
  rintro ⟨n, k⟩ ⟨hk, hkn, hc⟩
  have hn : n ∈ Set.Icc 2 a := rows_le a ⟨k, hk, hkn, hc⟩
  simp only [Set.mem_Icc, Prod.mk_le_mk] at hn ⊢
  omega

private theorem key (a : ℕ) :
    {p : ℕ × ℕ | 1 ≤ p.2 ∧ 2 * p.2 ≤ p.1 ∧ Nat.choose p.1 p.2 = a}.encard =
      ({n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ Nat.choose n k = a}.ncard : ℕ∞) := by
  rw [rows_eq_pairs a, (pairs_finite a).cast_ncard_eq]
-- opn-pair-proof: helpers end
set_option maxHeartbeats 1000000 in
theorem opnDirection : C_c_ae9bea28_p.opnClaim → C_c_fb339e85_p.opnClaim := by
  intro h
  -- opn-pair-proof: proof begins (an indented tactic block, to the end of the file)
  unfold C_c_ae9bea28_p.opnClaim at h
  unfold C_c_fb339e85_p.opnClaim
  intro t ht
  obtain ⟨a, ha⟩ := h t ht
  exact ⟨a, by rw [key a, ha]⟩
