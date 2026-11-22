/-! Non-vacuity witness (D-4 step 7): n = 3 exceeds 2. -/

theorem witness : ∃ (n : ℕ), (2 : ℕ) < n := ⟨3, by norm_num⟩
