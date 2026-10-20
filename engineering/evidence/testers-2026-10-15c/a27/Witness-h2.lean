import Mathlib

open scoped Nat

theorem witness : ∃ (c : ℝ), (0 : ℝ) < c := ⟨1, one_pos⟩
