/-! Non-vacuity witness (D-4 step 7): r = 2 satisfies 2 ≤ r. -/

theorem witness : ∃ (r : ℕ), (2 : ℕ) ≤ r := ⟨2, le_refl 2⟩
