/-! Non-vacuity witness (D-4 step 7): the binders carry no hypothesis; the one-vertex graph with no edges. -/

theorem witness : ∃ (V : Type) (inst : Fintype V) (inst : DecidableEq V) (G : SimpleGraph V) (inst : DecidableRel G.Adj), True :=
  ⟨Fin 1, inferInstance, inferInstance, ⊥, inferInstance, trivial⟩
