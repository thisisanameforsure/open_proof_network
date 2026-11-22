/-! Non-vacuity witness (D-4 step 7): P = Q = R = 1: monic, with the single coefficient 1, and 1 = 1 * 1. -/

theorem witness : ∃ (P Q R : Polynomial ℝ),
  P.Monic ∧ Q.Monic ∧ (∀ c ∈ P.coeffs, (0 : ℝ) ≤ c) ∧ (∀ c ∈ Q.coeffs, (0 : ℝ) ≤ c) ∧ R = P * Q ∧
    Mathoverflow339137.IsZeroOne R :=
  ⟨1, 1, 1, Polynomial.monic_one, Polynomial.monic_one,
    fun c hc => by simp [Polynomial.coeffs_one] at hc; simp [hc],
    fun c hc => by simp [Polynomial.coeffs_one] at hc; simp [hc],
    (mul_one 1).symm,
    by simp [Mathoverflow339137.IsZeroOne, Polynomial.coeffs_one]⟩
