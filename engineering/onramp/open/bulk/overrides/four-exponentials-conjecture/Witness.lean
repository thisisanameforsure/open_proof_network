/-! Non-vacuity witness (D-4 step 7): the pair (1, i) is ℚ-linearly independent in ℂ, taken for both x and y. -/

theorem witness : ∃ (x : Fin 2 → ℂ) (y : Fin 2 → ℂ), LinearIndependent ℚ x ∧ LinearIndependent ℚ y := by
  have h : LinearIndependent ℚ ![(1 : ℂ), Complex.I] := by
    rw [LinearIndependent.pair_iff]
    intro s t hst
    have h1 := congrArg Complex.re hst
    have h2 := congrArg Complex.im hst
    simp at h1 h2
    exact ⟨h1, h2⟩
  exact ⟨_, _, h, h⟩
