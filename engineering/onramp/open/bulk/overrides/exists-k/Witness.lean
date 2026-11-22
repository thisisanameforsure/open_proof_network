/-! Non-vacuity witness (D-4 step 7): n = 2 exceeds 1. -/

theorem witness : ∃ (n : ℕ), (1 : ℕ) < n := ⟨2, by norm_num⟩
