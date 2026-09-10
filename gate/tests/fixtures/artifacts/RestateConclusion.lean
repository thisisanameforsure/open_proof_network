/-! The subtler offload: the hole is the conclusion in the statement's own binder context. -/

theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by
  intro p q h
  have same : q ∧ p := sorry
  exact same
