import Nodes.«bad-statement».Context

/-! Does not elaborate: `1` is a Nat where a Prop is wanted. -/

theorem OpnProp.broken : ∀ p : Prop, p ∧ (1 : Nat) := by
  sorry
