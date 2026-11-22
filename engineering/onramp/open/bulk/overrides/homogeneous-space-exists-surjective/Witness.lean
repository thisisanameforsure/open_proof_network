/-! Non-vacuity witness (D-4 step 7): the one-point space is compact Hausdorff. -/

theorem witness : ∃ (X : Type) (_ : TopologicalSpace X), T2Space X ∧ CompactSpace X :=
  ⟨Unit, inferInstance, inferInstance, inferInstance⟩
