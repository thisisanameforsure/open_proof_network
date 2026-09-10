/-! A reduction (D-12 #4): a partial with exactly one hole, and the hole is a genuinely
different statement — commutativity as an iff — rather than the goal wearing a new name. -/

theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by
  intro p q h
  have comm : ∀ a b : Prop, (a ∧ b) ↔ (b ∧ a) := sorry
  exact (comm p q).mp h
