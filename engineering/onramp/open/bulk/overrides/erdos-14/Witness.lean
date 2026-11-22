/-! Non-vacuity witness (D-4 step 7): the empty set and ε = 1 > 0. -/

theorem witness : ∃ (A : Set ℕ) (ε : ℝ), ε > (0 : ℝ) := ⟨∅, 1, by norm_num⟩
