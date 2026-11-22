/-! Non-vacuity witness (D-4 step 7): the complete graph on two vertices is connected with minimum degree 1. (The statement itself lacks `[Fintype α]`, which `minDegree` needs; the witness supplies it.) -/

theorem witness : ∃ (α : Type) (_ : Fintype α) (G : SimpleGraph α) (_ : DecidableRel G.Adj),
    G.Connected ∧ (0 : ℕ) < G.minDegree :=
  ⟨Fin 2, inferInstance, ⊤, inferInstance, SimpleGraph.top_connected, by decide⟩
