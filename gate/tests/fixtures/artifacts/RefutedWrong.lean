/-! A counterexample of the wrong proposition: the conclusion is `p ∧ q`, not `q ∧ p`. -/

theorem OpnProp.and_swap_refuted : ¬ (∀ p q : Prop, p ∧ q → p ∧ q) := by
  sorry
