import Nodes.«unused-dep».Context

theorem OpnAdv.unused : ∀ p q : Prop, p ∧ q → q ∧ p := by
  intro p q h
  exact ⟨h.2, h.1⟩
