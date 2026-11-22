/-! Non-vacuity witness (D-4 step 7): the one-vertex graph is a tree with no edges, so n = 0. -/

theorem witness : ∃ (V : Type) (_ : Finite V) (T : SimpleGraph V) (n : ℕ), T.IsTree ∧ T.edgeSet.ncard = n :=
  ⟨Unit, inferInstance, ⊥, 0,
    ⟨SimpleGraph.connected_iff.2 ⟨fun u v => by rw [Subsingleton.elim u v], inferInstance⟩,
      fun v c hc => hc.not_nil (by cases c with
        | nil => rfl
        | cons h _ => exact h.elim)⟩,
    by simp⟩
