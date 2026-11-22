/-! Non-vacuity witness (D-4 step 7): ε = δ = 1 are positive reals. -/

theorem witness : ∃ (ε : ℝ) (δ : ℝ), ε > (0 : ℝ) ∧ δ > (0 : ℝ) := ⟨1, 1, by norm_num, by norm_num⟩
