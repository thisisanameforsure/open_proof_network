/-! Non-vacuity witness (D-4 step 7): n = 1 satisfies the bound n ≥ 1, so the conjecture's range is non-empty. -/

theorem witness : ∃ (n : ℕ), n ≥ (1 : ℕ) := ⟨1, le_refl 1⟩
