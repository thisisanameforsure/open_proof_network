import Mathlib

open scoped ArithmeticFunction.omega

theorem witness : ∃ (q : ℕ) (z : ℤ) (a : ℕ) (m : ℕ),
    (q : ℝ) * ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = (z : ℝ) ∧ a ≠ 0 :=
  ⟨0, 0, 1, 0, by simp, one_ne_zero⟩
