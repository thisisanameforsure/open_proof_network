/-! Non-vacuity witness (D-4 step 7): the empty graph on one vertex, with its decidable instances. -/

theorem witness : ∃ (V : Type) (inst : Fintype V) (inst : DecidableEq V) (G : SimpleGraph V) (inst : DecidableRel G.Adj), True :=
  ⟨Fin 1, inferInstance, inferInstance, ⊥, inferInstance, trivial⟩
