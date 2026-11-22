/-! Non-vacuity witness (D-4 step 7): √2 is algebraic over ℚ (a root of X² − 2) and irrational. -/

theorem witness : ∃ (x : ℝ), IsIrrationalAlgebraic x :=
  ⟨Real.sqrt 2, ⟨Polynomial.X ^ 2 - Polynomial.C 2, by
      intro h
      have := congrArg (Polynomial.coeff · 2) h
      simp at this,
    by simp [Real.sq_sqrt (show (0 : ℝ) ≤ 2 by norm_num)]⟩, irrational_sqrt_two⟩
