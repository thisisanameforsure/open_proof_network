/-! Non-vacuity witness (D-4 step 7): the one-point space, which is Hausdorff, compact, nonempty and (being discrete) monolithic. -/

theorem witness : ∃ (X : Type) (x : TopologicalSpace X),
    T2Space X ∧ CompactSpace X ∧ Nonempty X ∧ MonolithicSpace X :=
  ⟨Unit, inferInstance, inferInstance, inferInstance, inferInstance, inferInstance⟩
