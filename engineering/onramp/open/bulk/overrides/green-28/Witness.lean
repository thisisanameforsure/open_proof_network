/-! Non-vacuity witness (D-4 step 7): X = Y = the point mass at 0; both have finite support and their independent sum is again the point mass at 0, which is uniform on the singleton {0}. -/

theorem witness : ∃ (X : PMF ℤ) (Y : PMF ℤ),
    X.support.Finite ∧ Y.support.Finite ∧ IsUniformOnSupport (indepSum X Y) :=
  ⟨PMF.pure 0, PMF.pure 0, by simp, by simp,
    ⟨{0}, Finset.singleton_nonempty 0, by
      ext z
      simp [indepSum, PMF.pure_bind, PMF.pure_apply, PMF.uniformOfFinset_apply]⟩⟩
