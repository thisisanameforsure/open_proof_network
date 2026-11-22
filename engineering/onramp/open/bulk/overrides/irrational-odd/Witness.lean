/-! Non-vacuity witness (D-4 step 7): n = 1 is a positive natural, so the statement's hypothesis 0 < n is satisfiable. -/

theorem witness : ∃ (n : ℕ), (0 : ℕ) < n := ⟨1, by norm_num⟩
