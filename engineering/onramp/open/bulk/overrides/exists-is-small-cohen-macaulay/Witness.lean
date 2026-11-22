/-! Non-vacuity witness (D-4 step 7): the field ℚ is a local ring whose maximal ideal is ⊥, and every ring is complete for the ⊥-adic topology. (Written unchecked; the statement's `R` and `u` are free, so the closure's shape is a guess.) -/

theorem witness : ∃ (R : Type) (_ : CommRing R) (_ : IsLocalRing R),
    IsAdicComplete (IsLocalRing.maximalIdeal R) R :=
  ⟨ℚ, inferInstance, inferInstance, by rw [IsLocalRing.maximalIdeal_eq_bot]; infer_instance⟩
