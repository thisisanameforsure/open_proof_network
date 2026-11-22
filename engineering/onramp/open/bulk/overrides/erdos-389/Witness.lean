/-! Non-vacuity witness (D-4 step 7): n = 1 satisfies n ≥ 1. -/

theorem witness : ∃ (n : ℕ), n ≥ (1 : ℕ) := ⟨1, by norm_num⟩
