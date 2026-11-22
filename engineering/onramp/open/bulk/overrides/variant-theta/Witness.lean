/-! Non-vacuity witness (D-4 step 7): θ = 1/2 is positive and at most 1/2. -/

theorem witness : ∃ (θ : ℝ), 0 < θ ∧ θ ≤ 1/2 := ⟨1/2, by norm_num, le_refl _⟩
