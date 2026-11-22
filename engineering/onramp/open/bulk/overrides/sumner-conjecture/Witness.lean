/-! Non-vacuity witness (D-4 step 7): n = 2; the oriented tree is the single arc 0 → 1 on Fin 2 (an orientation of the complete graph on two vertices, a tree); the tournament is the same single arc on Fin 2, which has 2·2 − 2 = 2 vertices. -/

theorem witness : ∃ (n : ℕ) (W : Type) (inst : Fintype W) (inst_1 : DecidableEq W) (D : Digraph W)
    (inst_2 : DecidableRel D.Adj) (V : Type) (inst_3 : Fintype V) (inst_4 : DecidableEq V)
    (G : Digraph V) (inst_5 : DecidableRel G.Adj),
    2 ≤ n ∧ Fintype.card W = n ∧ SumnerUniversalTournamentConjecture.IsOrientedTree D ∧
      Fintype.card V = 2 * n - 2 ∧ G.IsTournament :=
  ⟨2, Fin 2, inferInstance, inferInstance, ⟨fun u v => u = 0 ∧ v = 1⟩,
    fun u v => inferInstanceAs (Decidable (u = 0 ∧ v = 1)),
    Fin 2, inferInstance, inferInstance, ⟨fun u v => u = 0 ∧ v = 1⟩,
    fun u v => inferInstanceAs (Decidable (u = 0 ∧ v = 1)),
    le_rfl, Fintype.card_fin 2,
    ⟨⊤, by
      rw [SimpleGraph.isTree_iff_connected_and_card]
      refine ⟨SimpleGraph.top_connected, ?_⟩
      rw [← SimpleGraph.edgeFinset_card, SimpleGraph.card_edgeFinset_top_eq_card_choose_two]
      simp,
     by unfold Digraph.IsOrientation; decide⟩,
    Fintype.card_fin 2, by unfold Digraph.IsTournament; decide⟩
