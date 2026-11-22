/-! Non-vacuity witness (D-4 step 7): n = m = 1 are positive. -/

theorem witness : ∃ (n : ℕ) (m : ℕ), (0 : ℕ) < n ∧ (0 : ℕ) < m := ⟨1, 1, one_pos, one_pos⟩
