/-! Non-vacuity witness (D-4 step 7): the one-vertex graph on `Fin 1` is a tree (connected, no cycles). -/

theorem witness : ∃ (W : Type) (inst : Fintype W) (inst : DecidableEq W) (T : SimpleGraph W) (inst : DecidableRel T.Adj), T.IsTree :=
  ⟨Fin 1, inferInstance, inferInstance, ⊥, inferInstance, by
    rw [SimpleGraph.isTree_iff_connected_and_card]
    refine ⟨⟨fun u v => by rw [Subsingleton.elim u v]⟩, ?_⟩
    simp⟩
