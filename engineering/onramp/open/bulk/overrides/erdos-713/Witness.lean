/-! Non-vacuity witness (D-4 step 7): the path on three vertices is bipartite (parts {0, 2} and {1}) and has the two edges 0–1 and 1–2. -/

theorem witness : ∃ (q : ℕ) (G : SimpleGraph (Fin q)), G.IsBipartite ∧ 2 ≤ G.edgeFinset.card := by
  refine ⟨3, SimpleGraph.pathGraph 3, ?_, ?_⟩
  · first
      | exact ⟨{0, 2}, {1}, by simp [Set.disjoint_left], fun v w h => by
          rw [SimpleGraph.pathGraph_adj] at h
          fin_cases v <;> fin_cases w <;> simp_all⟩
      | exact ⟨{0, 2}, {1}, by simp [Set.disjoint_left], fun {v w} h => by
          rw [SimpleGraph.pathGraph_adj] at h
          fin_cases v <;> fin_cases w <;> simp_all⟩
      | exact ⟨{0, 2}, {1}, by
          refine ⟨by simp [Set.disjoint_left], ?_⟩
          intro v w h
          rw [SimpleGraph.pathGraph_adj] at h
          fin_cases v <;> fin_cases w <;> simp_all⟩
  · have hsub : ({s((0 : Fin 3), (1 : Fin 3)), s((1 : Fin 3), (2 : Fin 3))} : Finset (Sym2 (Fin 3))) ⊆
        (SimpleGraph.pathGraph 3).edgeFinset := by
      intro e he
      simp only [Finset.mem_insert, Finset.mem_singleton] at he
      rcases he with rfl | rfl <;> simp [SimpleGraph.pathGraph_adj]
    have hne : s((0 : Fin 3), (1 : Fin 3)) ≠ s((1 : Fin 3), (2 : Fin 3)) := by decide
    calc 2 = ({s((0 : Fin 3), (1 : Fin 3)), s((1 : Fin 3), (2 : Fin 3))} : Finset (Sym2 (Fin 3))).card :=
          (Finset.card_pair hne).symm
      _ ≤ _ := Finset.card_le_card hsub
