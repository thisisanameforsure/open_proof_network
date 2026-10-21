import Nodes.«variant-refutes».Context

/-! A variant that refutes the root (D-30 v3.46): every instance of the root's hypothesis
denies its conclusion. False, as the root is true — and that is the point: proving this
statement would be a counterexample to the root by another road (D-12 #2). -/

theorem OpnProp.and_swap_reassoc_refuted :
    ∀ p q r : Prop, (p ∧ q) ∧ r → ¬(r ∧ (q ∧ p)) := by
  sorry
