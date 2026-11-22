/-! Non-vacuity witness (D-4 step 7): k = 1 is at least 1. -/

theorem witness : ∃ (k : ℕ), k ≥ (1 : ℕ) := ⟨1, le_refl 1⟩
