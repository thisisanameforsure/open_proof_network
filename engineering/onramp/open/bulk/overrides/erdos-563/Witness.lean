/-! Non-vacuity witness (D-4 step 7): α = 0 lies in [0, 1/2). -/

theorem witness : ∃ (α : ℝ), (0 : ℝ) ≤ α ∧ α < (1 / 2 : ℝ) := ⟨0, le_rfl, by norm_num⟩
