/-! Non-vacuity witness (D-4 step 7): the natural numbers with the discrete topology form a Hausdorff Toronto space (every subspace of the same cardinality is an infinite discrete space, hence homeomorphic to it). -/

theorem witness : ∃ (X : Type) (_ : TopologicalSpace X) (_ : T2Space X), TorontoSpace X :=
  ⟨ℕ, inferInstance, inferInstance, inferInstance⟩
