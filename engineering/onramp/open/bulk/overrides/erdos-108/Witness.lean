/-! Non-vacuity witness (D-4 step 7): r = 4 and k = 2 meet the two bounds. -/

theorem witness : ∃ (r : ℕ) (k : ℕ), r ≥ (4 : ℕ) ∧ k ≥ (2 : ℕ) := ⟨4, 2, le_rfl, le_rfl⟩
