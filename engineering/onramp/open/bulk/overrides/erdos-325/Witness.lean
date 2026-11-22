/-! Non-vacuity witness (D-4 step 7): k = 3 is at least 3. -/

theorem witness : ∃ (k : ℕ), (3 : ℕ) ≤ k := ⟨3, le_refl 3⟩
