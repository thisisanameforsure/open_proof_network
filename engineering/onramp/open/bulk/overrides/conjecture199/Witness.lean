/-! Non-vacuity witness (D-4 step 7): the one-vertex graph is connected and its largest induced tree has at most one vertex, so the connectivity bound holds with 1 - 2 = 0. -/

theorem witness : ∃ (α : Type) (G : SimpleGraph α), G.Connected ∧ largestInducedTreeSize G - 2 ≤ vertexConnectivity G :=
  ⟨Unit, ⊥, SimpleGraph.connected_iff.2 ⟨fun u v => by rw [Subsingleton.elim u v], inferInstance⟩, by
    have h : largestInducedTreeSize (⊥ : SimpleGraph Unit) ≤ 1 :=
      csSup_le' (by
        rintro n ⟨s, rfl, -⟩
        exact Finset.card_le_one.2 fun a _ b _ => Subsingleton.elim a b)
    omega⟩
