import Nodes.«variant-refutes».Context

-- relation: refutes
/-! The variant refutes the root: `variant → ¬root` (D-30 v3.46). Instantiate both at
`True` and the variant's conclusion denies the root's. -/

theorem relation :
    (∀ p q r : Prop, (p ∧ q) ∧ r → ¬(r ∧ (q ∧ p))) →
    ¬(∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p)) :=
  fun hV hR =>
    hV True True True ⟨⟨trivial, trivial⟩, trivial⟩
      (hR True True True ⟨⟨trivial, trivial⟩, trivial⟩)
