/-! Non-vacuity witness (D-4 step 7): k = 0 is an integer different from 1. -/

theorem witness : ∃ (k : ℤ) (k : ℤ), k ≠ (1 : ℤ) := ⟨0, 0, by norm_num⟩
