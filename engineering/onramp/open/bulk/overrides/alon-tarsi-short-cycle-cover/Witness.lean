/-! Non-vacuity witness (D-4 step 7): the one-vertex graph with no edges is bridgeless, since it has no edge to be a bridge. -/

theorem witness : ∃ (V : Type) (inst : Fintype V) (inst : DecidableEq V) (G : SimpleGraph V) (inst : DecidableRel G.Adj), G.IsBridgeless :=
  ⟨Fin 1, inferInstance, inferInstance, ⊥, inferInstance, fun e he => by simp at he⟩
