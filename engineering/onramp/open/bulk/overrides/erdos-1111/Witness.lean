/-! Non-vacuity witness (D-4 step 7): t = 1 and c = 1 are both at least 1. -/

theorem witness : ∃ (t : ℕ) (c : ℕ), (1 : ℕ) ≤ t ∧ (1 : ℕ) ≤ c := ⟨1, 1, le_refl 1, le_refl 1⟩
