/-! Non-vacuity witness (D-4 step 7): θ = 0 is below 1 and A = 1 is positive. -/

theorem witness : ∃ (θ : ℝ) (A : ℝ), θ < (1 : ℝ) ∧ (0 : ℝ) < A := ⟨0, 1, by norm_num, by norm_num⟩
