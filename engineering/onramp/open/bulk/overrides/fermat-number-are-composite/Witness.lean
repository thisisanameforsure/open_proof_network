/-! Non-vacuity witness (D-4 step 7): n = 5 exceeds 4. -/

theorem witness : ∃ (n : ℕ), n > (4 : ℕ) := ⟨5, by norm_num⟩
