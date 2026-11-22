/-! Non-vacuity witness (D-4 step 7): the empty language has countably many (indeed no) symbols, and the complete theory of the one-element structure is complete. -/

theorem witness : ∃ (L : FirstOrder.Language) (T : L.Theory), Countable L.Symbols ∧ T.IsComplete :=
  ⟨FirstOrder.Language.empty, FirstOrder.Language.completeTheory FirstOrder.Language.empty Unit,
    inferInstance, FirstOrder.Language.completeTheory.isComplete⟩
