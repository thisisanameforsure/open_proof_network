/-! Non-vacuity witness (D-4 step 7): ε = 1 is a positive real. -/

theorem witness : ∃ (ε : ℝ), ε > (0 : ℝ) := ⟨1, by norm_num⟩
