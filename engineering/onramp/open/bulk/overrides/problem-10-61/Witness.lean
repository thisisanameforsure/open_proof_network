/-! Non-vacuity witness (D-4 step 7): α = 3 is a Pisot number above 2: an algebraic integer whose minimal polynomial X - 3 has no other root. -/

theorem witness : ∃ (α : ℝ), IsPisot α ∧ (2 : ℝ) < α :=
  ⟨3, ⟨by norm_num, by simpa using isIntegral_algebraMap (R := ℤ) (A := ℝ) (x := 3), by
      intro z hz hne
      have h3 : (3 : ℝ) = algebraMap ℚ ℝ 3 := by simp
      rw [h3, minpoly.eq_X_sub_C', Polynomial.aroots_X_sub_C] at hz
      simp at hz hne
      exact hne hz⟩, by norm_num⟩
