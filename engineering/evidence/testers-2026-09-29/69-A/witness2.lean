import Mathlib

open scoped ArithmeticFunction.omega

theorem witness : ∃ (k : ℕ) (c : ℕ → ℕ), True := ⟨0, fun _ => 0, trivial⟩
