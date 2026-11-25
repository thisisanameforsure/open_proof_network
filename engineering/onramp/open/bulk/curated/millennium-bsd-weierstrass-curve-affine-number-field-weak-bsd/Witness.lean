/-! Non-vacuity witness (D-4 step 7): `ℚ`, lifted to the statement's universe, is a number field,
and y² = x³ - x is an elliptic curve over it (its discriminant is 64). -/

theorem witness : ∃ (K : Type*) (_ : Field K) (_ : DecidableEq K) (E : WeierstrassCurve.Affine K),
    NumberField K ∧ E.IsElliptic :=
  ⟨ULift ℚ, inferInstance, inferInstance, { a₁ := 0, a₂ := 0, a₃ := 0, a₄ := -1, a₆ := 0 },
    NumberField.of_ringEquiv ℚ (ULift ℚ) ULift.ringEquiv.symm,
    ⟨isUnit_iff_ne_zero.mpr (by
      simp only [WeierstrassCurve.Δ, WeierstrassCurve.b₂, WeierstrassCurve.b₄,
        WeierstrassCurve.b₆, WeierstrassCurve.b₈]
      intro h
      have := congrArg ULift.down h
      norm_num at this)⟩⟩
