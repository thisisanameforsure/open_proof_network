import Mathlib

open scoped ArithmeticFunction.omega

theorem cmp_root :
    (Irrational <| ∑' n, ω (n + 2) / 2 ^ (n + 2)) ↔
      Irrational (∑' n, ω (n + 2) / 2 ^ (n + 2) : ℝ) := Iff.rfl

theorem cmp_explicit :
    (∑' n, ω (n + 2) / 2 ^ (n + 2) : ℝ) = ∑' n : ℕ, ((ω (n + 2) : ℕ) : ℝ) / (2 : ℝ) ^ (n + 2) := rfl
