/-! Non-vacuity witness (D-4 step 7): the empty Young diagram. -/

theorem witness : ∃ (μ : YoungDiagram), True :=
  ⟨⊥, trivial⟩
