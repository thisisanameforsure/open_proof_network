import Nodes.«variant-backwards».Context

-- relation: partial
/-! Labelled `partial`, which claims the root implies the variant — but proves the
converse. The direction is the whole claim, so admission refuses this (D-30). -/

theorem relation :
    (∀ p q r : Prop, ((p ∧ q) ∧ r) ↔ (r ∧ (q ∧ p))) →
    (∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p)) :=
  fun h p q r x => (h p q r).mp x
