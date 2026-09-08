/-! Declared dependencies (D-4 step 8): signatures of `tutorial-and-swap` and `and-reassoc`. -/

theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by
  sorry

theorem OpnProp.and_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → p ∧ (q ∧ r) := by
  sorry
