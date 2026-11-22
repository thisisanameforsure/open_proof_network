/-! Non-vacuity witness (D-4 step 7): the complete graph on one vertex is connected, every vertex being reachable from itself. -/

theorem witness : ∃ (V : Type) (inst : Fintype V) (G : SimpleGraph V), G.Connected :=
  ⟨Fin 1, inferInstance, ⊤, ⟨fun u v => Subsingleton.elim u v ▸ SimpleGraph.Reachable.refl u⟩⟩
