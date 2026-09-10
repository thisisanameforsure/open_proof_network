/-! A plain proof (D-12 #1): the statement's own name and type. -/

theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by
  intro p q h
  exact ⟨h.2, h.1⟩
