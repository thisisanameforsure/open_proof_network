/-! Non-vacuity witness (D-4 step 7): t = 2, r = 2 and ε = 1 satisfy the three bounds. -/

theorem witness : ∃ (t : ℕ) (r : ℕ) (ε : ℝ), (2 : ℕ) ≤ t ∧ (2 : ℕ) ≤ r ∧ (0 : ℝ) < ε :=
  ⟨2, 2, 1, le_rfl, le_rfl, one_pos⟩
