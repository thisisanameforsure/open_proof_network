/-! Non-vacuity witness (D-4 step 7): c₁ = 1 and c₂ = 1 are positive. -/

theorem witness : ∃ (c₁ : ℝ) (c₂ : ℕ), c₁ > (0 : ℝ) ∧ c₂ > (0 : ℕ) := ⟨1, 1, by norm_num, by norm_num⟩
