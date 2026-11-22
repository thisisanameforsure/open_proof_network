/-! Non-vacuity witness (D-4 step 7): k = 4 and r = 1 meet the two bounds. -/

theorem witness : ∃ (k : ℕ) (r : ℕ), k ≥ (4 : ℕ) ∧ r ≥ (1 : ℕ) := ⟨4, 1, le_refl 4, le_refl 1⟩
