/-! Non-vacuity witness (D-4 step 7): the one-point space is Hausdorff, compact, homogeneous (the identity homeomorphism) and countably monolithic. -/

theorem witness : ∃ (X : Type) (_ : TopologicalSpace X),
    T2Space X ∧ CompactSpace X ∧ HomogeneousSpace X ∧ CountablyMonolithicSpace X :=
  ⟨Unit, inferInstance, inferInstance, inferInstance,
    ⟨fun _ _ => ⟨Homeomorph.refl Unit, Subsingleton.elim _ _⟩⟩,
    by constructor <;> intros <;> simp_all⟩
