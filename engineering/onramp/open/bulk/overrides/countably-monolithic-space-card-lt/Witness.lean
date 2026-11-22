/-! Non-vacuity witness (D-4 step 7): the one-point space is Hausdorff, compact and homogeneous (the identity homeomorphism carries its point to itself); the statement's fourth hypothesis, `CountablyMonolithicSpace`, is not among the ported definitions and so cannot be named here. -/

theorem witness : ∃ (X : Type) (x : TopologicalSpace X), T2Space X ∧ CompactSpace X ∧ HomogeneousSpace X :=
  ⟨Unit, inferInstance, inferInstance, inferInstance, ⟨fun x y => ⟨Homeomorph.refl Unit, Subsingleton.elim _ _⟩⟩⟩
