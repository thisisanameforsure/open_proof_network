import Mathlib

theorem witness : ∃ x : ℝ, ∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧ ∀ m : ℤ, (N.factorial : ℝ) * x ≠ m := by
  refine ⟨Real.sqrt 2, fun M => ⟨M, le_rfl, fun m h => ?_⟩⟩
  have hirr : Irrational ((M.factorial : ℚ) * Real.sqrt 2) := by
    have := irrational_sqrt_two.ratCast_mul (q := (M.factorial : ℚ)) (by exact_mod_cast Nat.factorial_ne_zero M)
    simpa using this
  apply hirr
  refine ⟨(m : ℚ), ?_⟩
  push_cast
  rw [h]
