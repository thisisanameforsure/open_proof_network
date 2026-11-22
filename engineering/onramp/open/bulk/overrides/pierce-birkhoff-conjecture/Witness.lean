/-! Non-vacuity witness (D-4 step 7): the zero function on ℝ^0 is piecewise polynomial, given by the single polynomial 0. -/

theorem witness : ∃ (n : ℕ) (f : (Fin n → ℝ) → ℝ), IsPiecewiseMvPolynomial f :=
  ⟨0, fun _ => 0, ⟨Unit, inferInstance, fun _ => 0, fun _ => ⟨(), by simp⟩⟩⟩
