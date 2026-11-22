/-! Non-vacuity witness (D-4 step 7): √2 is an irrational real, so the hypothesis Irrational t is satisfiable. -/

theorem witness : ∃ (t : ℝ), Irrational t := ⟨Real.sqrt 2, irrational_sqrt_two⟩
