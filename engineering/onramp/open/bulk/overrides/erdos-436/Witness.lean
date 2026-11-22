/-! Non-vacuity witness (D-4 step 7): k = 3 is odd and at least 3. -/

theorem witness : ∃ (k : ℕ), k ≥ (3 : ℕ) ∧ Odd k := ⟨3, le_refl 3, by decide⟩
