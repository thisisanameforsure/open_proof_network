/-! Non-vacuity witness (D-4 step 7): c = 1 exceeds 1/2. -/

theorem witness : ∃ (c : ℝ), c > (1 / 2 : ℝ) :=
  ⟨1, by norm_num⟩
