/-! Non-vacuity witness (D-4 step 7): x = y = 1 are positive naturals. -/

theorem witness : ∃ (x : ℕ) (y : ℕ), (0 : ℕ) < x ∧ (0 : ℕ) < y := ⟨1, 1, by norm_num, by norm_num⟩
