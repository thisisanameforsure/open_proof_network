/-! Non-vacuity witness (D-4 step 7): the one-vertex graph is a tree with n = 0 edges. -/

theorem witness : ∃ (V : Type) (_ : Finite V) (T : SimpleGraph V) (n : ℕ),
    T.IsTree ∧ T.edgeSet.ncard = n :=
  ⟨Unit, inferInstance, ⊥, 0,
   ⟨⟨fun u v => by rw [Subsingleton.elim u v]⟩, SimpleGraph.isAcyclic_bot⟩,
   by simp⟩
