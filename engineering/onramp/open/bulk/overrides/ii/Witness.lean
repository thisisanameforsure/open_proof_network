/-! Non-vacuity witness (D-4 step 7): x = 2 satisfies 2 ≤ x. -/

theorem witness : ∃ (x : ℕ), (2 : ℕ) ≤ x := ⟨2, le_rfl⟩
