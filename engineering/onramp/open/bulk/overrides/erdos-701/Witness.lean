/-! Non-vacuity witness (D-4 step 7): the one-point type with the empty family, which is a lower set. -/

theorem witness : ∃ (X : Type) (_ : Nonempty X) (_ : Fintype X) (F : Set (Set X)), IsLowerSet F :=
  ⟨Unit, inferInstance, inferInstance, ∅, isLowerSet_empty⟩
