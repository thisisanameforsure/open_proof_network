/-! Non-vacuity witness (D-4 step 7): k = 3 and the complete graph on four vertices, whose minimum degree is 3. -/

theorem witness : ∃ (k : ℕ) (V : Type) (_ : Fintype V) (_ : DecidableEq V) (G : SimpleGraph V)
    (_ : DecidableRel G.Adj), 3 ≤ k ∧ k ≤ G.minDegree :=
  ⟨3, Fin 4, inferInstance, inferInstance, ⊤, inferInstance, le_refl 3,
    SimpleGraph.le_minDegree_of_forall_le_degree 3 fun v => by
      rw [SimpleGraph.complete_graph_degree]; simp⟩
