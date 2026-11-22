/-! Non-vacuity witness (D-4 step 7): α = √2, an irrational real greater than 1. -/

theorem witness : ∃ (α : ℝ), α > 1 ∧ Irrational α :=
  ⟨Real.sqrt 2, (Real.lt_sqrt (by norm_num)).2 (by norm_num), irrational_sqrt_two⟩
