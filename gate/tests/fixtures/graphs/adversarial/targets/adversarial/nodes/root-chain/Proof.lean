import Nodes.«root-chain».Context

theorem OpnProp.and_swap_reassoc : ∀ p q r : Prop, (p ∧ q) ∧ r → r ∧ (q ∧ p) := by
  intro p q r h
  have h2 := OpnProp.and_reassoc p q r h
  exact ⟨h2.2.2, OpnProp.and_swap p q h.1⟩
