/-! Non-vacuity witness (D-4 step 7): r = 3 satisfies 3 ≤ r. -/

theorem witness : ∃ (r : ℕ), (3 : ℕ) ≤ r := ⟨3, le_refl 3⟩
