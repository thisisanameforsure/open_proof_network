import Mathlib

open scoped ArithmeticFunction.omega

theorem witness : ∃ (q : ℕ) (z : ℤ) (a Q b T : ℕ),
    (q : ℝ) * ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = (z : ℝ) ∧ a ≠ 0 ∧ 0 < T ∧
      ∀ p ∈ a.primeFactors, Nat.Coprime p Q :=
  ⟨0, 0, 1, 1, 0, 1, by simp, one_ne_zero, one_pos, by simp⟩
