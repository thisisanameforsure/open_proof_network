/-! Non-vacuity witness (D-4 step 7): p = 2, q = 3 (multiplicatively independent) and Haar probability measure on the circle, which is atomless and preserved by x ↦ 2x and x ↦ 3x. -/

theorem witness : ∃ (p q : ℕ) (μ : Measure 𝕋), 2 ≤ p ∧ 2 ≤ q ∧ MultiplicativelyIndependent p q ∧ IsProbabilityMeasure μ ∧ IsAtomLess μ ∧ MeasurePreserving (Tn p) μ μ ∧ MeasurePreserving (Tn q) μ μ :=
  ⟨2, 3, volume, le_rfl, by norm_num, by decide, inferInstance, inferInstance,
    AddCircle.measurePreserving_nsmul (by norm_num), AddCircle.measurePreserving_nsmul (by norm_num)⟩
