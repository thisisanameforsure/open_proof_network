import Mathlib

open scoped ArithmeticFunction.omega

theorem witness : ∃ (f : ℕ → ℕ) (q : ℚ), Summable (fun n : ℕ => (f n : ℝ) / 2 ^ n) ∧
    (q : ℝ) = ∑' n : ℕ, (f n : ℝ) / 2 ^ n :=
  ⟨fun _ => 0, 0, by simp, by simp⟩
