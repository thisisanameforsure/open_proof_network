/-! Non-vacuity witness (D-4 step 7): n = 5 satisfies 5 ≤ n. -/

theorem witness : ∃ (n : ℕ), (5 : ℕ) ≤ n := ⟨5, le_refl 5⟩
