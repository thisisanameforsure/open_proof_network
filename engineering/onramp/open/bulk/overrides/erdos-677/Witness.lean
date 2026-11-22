/-! Non-vacuity witness (D-4 step 7): m = 1, n = 0, k = 1: k is positive and m ≥ n + k. -/

theorem witness : ∃ (m : ℕ) (n : ℕ) (k : ℕ), k > 0 ∧ m ≥ n + k :=
  ⟨1, 0, 1, one_pos, by norm_num⟩
