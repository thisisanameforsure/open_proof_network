/-! Non-vacuity witness (D-4 step 7): n = 3 is at least 3. -/

theorem witness : ∃ (n : ℕ), n ≥ (3 : ℕ) := ⟨3, le_refl 3⟩
