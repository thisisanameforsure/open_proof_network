/-! Non-vacuity witness (D-4 step 7): the complete graph on two vertices is 1-regular. -/

theorem witness : ∃ (V : Type) (_ : Fintype V) (_ : DecidableEq V) (G : SimpleGraph V)
    (_ : DecidableRel G.Adj) (r : ℕ), (∀ v, G.degree v = r) ∧ (1 : ℕ) ≤ r :=
  ⟨Fin 2, inferInstance, inferInstance, ⊤, inferInstance, 1, by decide, le_refl 1⟩
