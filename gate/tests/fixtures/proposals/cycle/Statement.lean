import Nodes.«cycle».Context

/-! Declares the root as a dependency; the test makes the root depend back. -/

theorem OpnProp.circular : ∀ p : Prop, p → p := by
  sorry
