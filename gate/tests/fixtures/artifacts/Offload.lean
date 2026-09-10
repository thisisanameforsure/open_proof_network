/-! The offload rule's first shape: the hole is the whole statement under a new name. -/

theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by
  have restated : ∀ p q : Prop, p ∧ q → q ∧ p := sorry
  exact restated
