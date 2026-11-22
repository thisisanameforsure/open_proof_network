/-! Non-vacuity witness (D-4 step 7): the Cantor space ℕ → Bool is infinite, Hausdorff and compact, and homogeneous because coordinatewise swaps are homeomorphisms carrying any point to any other. -/

theorem witness : ∃ (X : Type) (_ : TopologicalSpace X), ¬ Finite X ∧ T2Space X ∧ CompactSpace X ∧ HomogeneousSpace X :=
  ⟨ℕ → Bool, inferInstance, not_finite _, inferInstance, inferInstance,
    ⟨fun x y => ⟨Homeomorph.piCongrRight fun i =>
      ⟨Equiv.swap (x i) (y i), continuous_of_discreteTopology, continuous_of_discreteTopology⟩,
      funext fun i => Equiv.swap_apply_left _ _⟩⟩⟩
