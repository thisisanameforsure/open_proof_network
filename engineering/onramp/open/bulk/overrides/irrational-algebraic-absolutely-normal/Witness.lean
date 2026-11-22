/-! Non-vacuity witness (D-4 step 7): √2 is a root of X² − 2 and is irrational. -/

theorem witness : ∃ (x : ℝ), AlgebraicNormality.IsIrrationalAlgebraic x :=
  ⟨Real.sqrt 2,
   ⟨Polynomial.X ^ 2 - Polynomial.C 2, Polynomial.X_pow_sub_C_ne_zero two_pos 2,
    by simp [Real.sq_sqrt (by norm_num : (0 : ℝ) ≤ 2)]⟩,
   irrational_sqrt_two⟩
