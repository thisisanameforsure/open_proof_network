/-! Non-vacuity witness (D-4 step 7): two copies of the empty graph on three vertices are hypomorphic through the identity (every vertex-deleted subgraph is the empty graph on two vertices). (Written unchecked; `Hypomorphic` is not defined by any ported module, so its unfolding below is a guess.) -/

theorem witness : ∃ (V W : Type) (_ : Fintype V) (_ : Fintype W) (G : SimpleGraph V) (H : SimpleGraph W),
    3 ≤ Fintype.card V ∧ Hypomorphic G H :=
  ⟨Fin 3, Fin 3, inferInstance, inferInstance, ⊥, ⊥, by simp,
    ⟨Equiv.refl _, fun v => ⟨SimpleGraph.Iso.refl _⟩⟩⟩
