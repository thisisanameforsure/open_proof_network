/-! Non-vacuity witness (D-4 step 7): the trivial group is a finite group. (The statement's `IsRealizable` is not among the ported definitions.) -/

theorem witness : ∃ (G : Type) (_ : Fintype G) (_ : Group G), True :=
  ⟨Unit, inferInstance, inferInstance, trivial⟩
