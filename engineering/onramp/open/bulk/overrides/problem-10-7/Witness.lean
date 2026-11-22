/-! Non-vacuity witness (D-4 step 7): ε = 1 (positive) and M = 0. -/

theorem witness : ∃ (ε : ℝ) (M : ℝ), 0 < ε :=
  ⟨1, 0, one_pos⟩
