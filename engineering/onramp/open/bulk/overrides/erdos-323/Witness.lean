/-! Non-vacuity witness (D-4 step 7): k = 1 and ε = 1. -/

theorem witness : ∃ (k : ℕ) (ε : ℝ), k ≥ 1 ∧ ε > (0 : ℝ) := ⟨1, 1, le_refl 1, by norm_num⟩
