/-! Non-vacuity witness (D-4 step 7): n = 1 is a positive natural number. -/

theorem witness : ∃ (n : ℕ), n > (0 : ℕ) := ⟨1, by norm_num⟩
