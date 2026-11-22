/-! Non-vacuity witness (D-4 step 7): the empty graph on a one-point finite type. -/

theorem witness : ∃ (V : Type) (inst : Fintype V) (G : SimpleGraph V), True :=
  ⟨Unit, inferInstance, ⊥, trivial⟩
