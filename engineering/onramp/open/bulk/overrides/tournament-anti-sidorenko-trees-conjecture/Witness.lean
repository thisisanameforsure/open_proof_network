/-! Non-vacuity witness (D-4 step 7): the one-vertex graph with no edges is a tree. -/

theorem witness : ∃ (V : Type u_1) (inst : Fintype V) (inst : DecidableEq V) (T : SimpleGraph V) (inst : DecidableRel T.Adj), T.IsTree :=
  ⟨PUnit, inferInstance, inferInstance, ⊥, inferInstance, by
    rw [SimpleGraph.isTree_iff_connected_and_card]
    exact ⟨⟨SimpleGraph.bot_preconnected_iff_subsingleton.2 inferInstance⟩, by simp⟩⟩
