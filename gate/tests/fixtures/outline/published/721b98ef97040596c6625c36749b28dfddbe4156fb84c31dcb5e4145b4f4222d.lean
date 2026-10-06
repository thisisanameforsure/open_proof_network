/-! The tutorial node (D-27): permanently open, off-ledger. Lean core only. -/

theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by
  intro p q h
  exact ⟨h.2, h.1⟩
