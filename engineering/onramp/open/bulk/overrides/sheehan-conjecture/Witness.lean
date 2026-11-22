/-! Non-vacuity witness (D-4 step 7): the complete graph K₅ on Fin 5 is 4-regular and 0 → 1 → 2 → 3 → 4 → 0 is a Hamiltonian cycle in it. -/

theorem witness : ∃ (V : Type) (inst : Fintype V) (inst_1 : DecidableEq V) (G : SimpleGraph V) (inst_2 : DecidableRel G.Adj) (v : V)
  (c : G.Walk v v), (∀ (v : V), G.degree v = (4 : ℕ)) ∧ LovaszPlummerConjecture.IsHamiltonianCycle G c :=
  ⟨Fin 5, inferInstance, inferInstance, ⊤, inferInstance, 0,
    SimpleGraph.Walk.cons (v := 1) (by decide) (SimpleGraph.Walk.cons (v := 2) (by decide)
      (SimpleGraph.Walk.cons (v := 3) (by decide) (SimpleGraph.Walk.cons (v := 4) (by decide)
        (SimpleGraph.Walk.cons (v := 0) (by decide) SimpleGraph.Walk.nil)))),
    fun v => by simp [SimpleGraph.complete_graph_degree],
    ⟨by rw [SimpleGraph.Walk.isCycle_def]; exact ⟨by decide, by decide, by decide⟩, by decide⟩⟩
