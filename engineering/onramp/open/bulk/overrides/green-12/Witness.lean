/-! Non-vacuity witness (D-4 step 7): the binders carry no hypothesis; the trivial group with the empty set of elements. -/

theorem witness : ∃ (G : Type _) (inst : AddCommGroup G) (inst : Fintype G) (inst : DecidableEq G) (A : Finset G), True :=
  ⟨Unit, inferInstance, inferInstance, inferInstance, ∅, trivial⟩
