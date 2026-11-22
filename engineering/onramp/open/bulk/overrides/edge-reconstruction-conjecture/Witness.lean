/-! Non-vacuity witness (D-4 step 7): the complete graph on four vertices has six edges and is edge-hypomorphic to itself (the identity on edges, the identity isomorphism after deleting any edge). -/

theorem witness : ∃ (V : Type) (inst : Fintype V) (G H : SimpleGraph V), (4 : ℕ) ≤ G.edgeSet.ncard ∧ EdgeHypomorphic G H :=
  ⟨Fin 4, inferInstance, ⊤, ⊤, by
      rw [Set.ncard_eq_toFinset_card', SimpleGraph.edgeFinset, SimpleGraph.card_edgeFinset_top_eq_card_choose_two]
      decide,
    ⟨Equiv.refl _, fun _ => ⟨SimpleGraph.Iso.refl _⟩⟩⟩
