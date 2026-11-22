/-! Non-vacuity witness (D-4 step 7): the rational t = 2 exceeds 1. -/

theorem witness : ∃ (t : ℚ), t > (1 : ℚ) := ⟨2, by norm_num⟩
