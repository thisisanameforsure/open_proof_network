/-! Non-vacuity witness (D-4 step 7): the polynomial g = X over ℚ has degree 1, takes the integer value n at every natural n, and is positive for every n ≥ 1, so the three hypotheses are jointly satisfiable. -/

theorem witness : ∃ (g : Polynomial ℚ),
  (0 : ℕ) < g.natDegree ∧
    (∀ (n : ℕ), ∃ (k : ℤ), Polynomial.eval (↑n : ℚ) g = (↑k : ℚ)) ∧
      ∀ᶠ (n : ℕ) in Filter.atTop, (0 : ℚ) < Polynomial.eval (↑n : ℚ) g :=
  ⟨Polynomial.X, by simp, fun n => ⟨n, by simp⟩,
    Filter.eventually_atTop.2 ⟨1, fun n hn => by rw [Polynomial.eval_X]; exact Nat.cast_pos.2 hn⟩⟩
