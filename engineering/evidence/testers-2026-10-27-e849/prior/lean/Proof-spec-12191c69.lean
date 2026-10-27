import Mathlib
import Nodes.«spec-12191c69».Context

open Nat

private theorem step_lt (n k : ℕ) (h : 2 * (k + 1) ≤ n) : choose n k < choose n (k + 1) := by
  have e := Nat.choose_succ_right_eq n k
  have hp : 0 < choose n k := Nat.choose_pos (by omega)
  have hk : k + 1 < n - k := by omega
  by_contra hc
  push_neg at hc
  have : choose n k * (n - k) ≤ choose n k * (k + 1) := by
    calc choose n k * (n - k) = choose n (k + 1) * (k + 1) := e.symm
      _ ≤ choose n k * (k + 1) := Nat.mul_le_mul_right _ hc
  have := Nat.le_of_mul_le_mul_left this hp
  omega

private theorem mono_lt (n : ℕ) : ∀ j i : ℕ, i < j → 2 * j ≤ n → choose n i < choose n j := by
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
    (h : choose n k₁ = choose n k₂) : k₁ = k₂ := by
  rcases lt_trichotomy k₁ k₂ with hl | he | hg
  · have := mono_lt n k₂ k₁ hl h₂; omega
  · exact he
  · have := mono_lt n k₁ k₂ hg h₁; omega

/-- Erdős 849, structure: the root counts rows `n`; the problem counts solutions `(n, k)`.
For every `a` the two counts agree, because `C(n, ·)` is strictly increasing on
`0 ≤ k ≤ n/2`, so a row holds the value `a` at most once in that range. -/
theorem Opn.erdos_849_rows_eq_pairs : ∀ a : ℕ,
    {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ choose n k = a}.ncard =
      {p : ℕ × ℕ | 1 ≤ p.2 ∧ 2 * p.2 ≤ p.1 ∧ choose p.1 p.2 = a}.ncard := by
  intro a
  have himg : (Prod.fst '' {p : ℕ × ℕ | 1 ≤ p.2 ∧ 2 * p.2 ≤ p.1 ∧ choose p.1 p.2 = a}) =
      {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ choose n k = a} := by
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
