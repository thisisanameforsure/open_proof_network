/-! Non-vacuity witness (D-4 step 7): the empty graph on no vertices; no vertex set has two elements, so the sparsity condition holds vacuously. -/

theorem witness : ∃ (p : ℕ) (G : SimpleGraph (Fin p)),
    ∀ S : Finset (Fin p), 2 ≤ S.card → (G.induce S).edgeSet.ncard ≤ 2 * S.card - 3 :=
  ⟨0, ⊥, fun S hS => by
    have := Finset.card_le_univ S
    rw [Fintype.card_fin] at this
    omega⟩
