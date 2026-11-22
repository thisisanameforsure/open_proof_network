/-! Non-vacuity witness (D-4 step 7): ε = 1 is positive and ℓ = 1 meets the bound. -/

theorem witness : ∃ (ε : ℝ) (ℓ : ℕ), (0 : ℝ) < ε ∧ (1 : ℕ) ≤ ℓ := ⟨1, 1, by norm_num, le_rfl⟩
