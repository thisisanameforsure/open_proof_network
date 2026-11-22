/-! Non-vacuity witness (D-4 step 7): n = 2 is at least 2. -/

theorem witness : ∃ (n : ℕ), (2 : ℕ) ≤ n := ⟨2, le_refl 2⟩
