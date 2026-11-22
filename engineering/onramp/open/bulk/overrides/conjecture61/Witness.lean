/-! Non-vacuity witness (D-4 step 7): the complete graph on a one-point type, which is connected. -/

theorem witness : ∃ (α : Type u_1) (G : SimpleGraph α) (inst : DecidableRel G.Adj), G.Connected :=
  ⟨PUnit, ⊤, inferInstance, SimpleGraph.top_connected⟩
