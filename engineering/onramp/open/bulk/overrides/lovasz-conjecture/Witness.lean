/-! Non-vacuity witness (D-4 step 7): the one-vertex complete graph is connected and vertex-transitive (the identity isomorphism). -/

theorem witness : ∃ (V : Type) (inst : Fintype V) (inst : DecidableEq V) (G : SimpleGraph V) (inst : DecidableRel G.Adj),
    G.Connected ∧ LovaszConjecture.IsVertexTransitive G :=
  ⟨Fin 1, inferInstance, inferInstance, ⊤, inferInstance,
   ⟨fun u v => Subsingleton.elim u v ▸ SimpleGraph.Reachable.refl u⟩,
   fun u v => ⟨SimpleGraph.Iso.refl, Subsingleton.elim _ _⟩⟩
