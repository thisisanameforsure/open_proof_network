/-! Non-vacuity witness (D-4 step 7): the complete graph K₄ on four vertices is cubic and bridgeless. -/

theorem witness : ∃ (V : Type) (_ : Fintype V) (_ : DecidableEq V) (G : SimpleGraph V) (_ : DecidableRel G.Adj), IsCubic G ∧ G.IsBridgeless :=
  ⟨Fin 4, inferInstance, inferInstance, ⊤, inferInstance, by decide, by decide⟩
