/-! Non-vacuity witness (D-4 step 7): x = 0, where 2^0 = 1 and 3^0 = 1 are both natural numbers. -/

theorem witness : ∃ (x : ℝ), (∃ (m : ℕ), (2 : ℝ) ^ x = (↑m : ℝ)) ∧ ∃ (m : ℕ), (3 : ℝ) ^ x = (↑m : ℝ) :=
  ⟨0, ⟨1, by simp⟩, ⟨1, by simp⟩⟩
