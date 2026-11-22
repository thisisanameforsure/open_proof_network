/-! Non-vacuity witness (D-4 step 7): x = 2. -/

theorem witness : ∃ (x : ℕ), 2 ≤ x :=
  ⟨2, le_rfl⟩
