/-! Non-vacuity witness (D-4 step 7): ε = 1 is a positive real. -/

theorem witness : ∃ (ε : ℝ), (0 : ℝ) < ε := ⟨1, by norm_num⟩
