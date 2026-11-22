/-! Non-vacuity witness (D-4 step 7): ε = 1 and η = 1, both positive. -/

theorem witness : ∃ (ε : ℝ) (η : EReal), ε > 0 ∧ η > 0 :=
  ⟨1, 1, one_pos, zero_lt_one⟩
