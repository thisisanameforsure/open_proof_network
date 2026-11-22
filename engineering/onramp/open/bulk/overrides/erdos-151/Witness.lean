/-! Non-vacuity witness (D-4 step 7): the empty graph on no vertices. -/

theorem witness : ∃ (n : ℕ) (G : SimpleGraph (Fin n)), True := ⟨0, ⊥, trivial⟩
