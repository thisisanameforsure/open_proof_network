/-! Non-vacuity witness (D-4 step 7): α = 0, which lies in [0, 1/2). -/

theorem witness : ∃ (α : ℝ), 0 ≤ α ∧ α < 1 / 2 :=
  ⟨0, le_rfl, by norm_num⟩
