/-! Non-vacuity witness (D-4 step 7): y² = x³ - x is an elliptic curve over ℚ (its discriminant is 64). -/

theorem witness : ∃ (E : WeierstrassCurve.Affine ℚ), E.IsElliptic :=
  ⟨{ a₁ := 0, a₂ := 0, a₃ := 0, a₄ := -1, a₆ := 0 },
    ⟨isUnit_iff_ne_zero.mpr (by
      simp only [WeierstrassCurve.Δ, WeierstrassCurve.b₂, WeierstrassCurve.b₄,
        WeierstrassCurve.b₆, WeierstrassCurve.b₈]
      norm_num)⟩⟩
