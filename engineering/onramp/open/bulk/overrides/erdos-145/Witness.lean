/-! Non-vacuity witness (D-4 step 7): α = 0 is a non-negative exponent. -/

theorem witness : ∃ (α : ℝ), α ≥ (0 : ℝ) := ⟨0, le_refl 0⟩
