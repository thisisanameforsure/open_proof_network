theorem OpnProp.and_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) := by
  intro p q r h
  exact ⟨h.1.1, h.1.2, h.2⟩
