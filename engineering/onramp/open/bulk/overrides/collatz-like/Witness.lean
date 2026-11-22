/-! Non-vacuity witness (D-4 step 7): n = 9 exceeds 8. -/

theorem witness : ∃ (n : ℕ), (8 : ℕ) < n := ⟨9, by norm_num⟩
