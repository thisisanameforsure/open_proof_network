/-! Non-vacuity witness (D-4 step 7): the empty graph on one vertex (no leading binder carries a hypothesis). -/

theorem witness : ∃ (V : Type) (inst : Fintype V) (G : SimpleGraph V) (inst_1 : DecidableRel G.Adj), True :=
  ⟨Fin 1, inferInstance, ⊥, inferInstance, trivial⟩
