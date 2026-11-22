/-! Non-vacuity witness (D-4 step 7): the one-vertex graph with no edges is a tree. -/

theorem witness : ∃ (V : Type*) (_ : Fintype V) (_ : DecidableEq V) (T : SimpleGraph V)
    (_ : DecidableRel T.Adj), T.IsTree :=
  ⟨Fin 1, inferInstance, inferInstance, ⊥, inferInstance,
    ⟨⟨fun u v => (Subsingleton.elim u v) ▸ SimpleGraph.Reachable.refl u, inferInstance⟩,
      SimpleGraph.isAcyclic_bot⟩⟩
