import Nodes.«variant-resolves».Context

-- relation: resolves
/-! The variant implies the root: proving the iff closes the target (D-30). -/

theorem relation :
    (∀ p q r : Prop, ((p ∧ q) ∧ r) ↔ (r ∧ (q ∧ p))) →
    (∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p)) :=
  fun h p q r x => (h p q r).mp x
