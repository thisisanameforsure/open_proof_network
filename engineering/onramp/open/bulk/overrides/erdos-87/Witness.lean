/-! Non-vacuity witness (D-4 step 7): ε = 1/2 lies strictly between 0 and 1. -/

theorem witness : ∃ (ε : ℝ), ε > (0 : ℝ) ∧ ε < (1 : ℝ) := ⟨1 / 2, by norm_num, by norm_num⟩
