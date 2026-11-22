/-! Non-vacuity witness (D-4 step 7): c = 1 is a positive real, so the leading bound c > 0 is satisfiable. -/

theorem witness : ∃ (c : ℝ), c > (0 : ℝ) := ⟨1, by norm_num⟩
