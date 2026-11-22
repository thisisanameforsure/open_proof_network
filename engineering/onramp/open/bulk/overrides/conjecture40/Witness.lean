/-! Non-vacuity witness (D-4 step 7): the complete graph on two vertices is connected and has more than one vertex. -/

theorem witness : ∃ (α : Type) (inst : Fintype α) (inst_1 : DecidableEq α) (G : SimpleGraph α), G.Connected ∧ (1 : ℕ) < Fintype.card α :=
  ⟨Fin 2, inferInstance, inferInstance, ⊤,
    ⟨fun u v => by
      by_cases h : u = v
      · subst h; exact SimpleGraph.Reachable.refl _
      · exact SimpleGraph.Adj.reachable (SimpleGraph.top_adj.mpr h)⟩,
    by simp⟩
