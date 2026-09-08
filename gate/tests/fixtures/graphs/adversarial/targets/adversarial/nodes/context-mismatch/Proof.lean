import Nodes.«context-mismatch».Context

theorem OpnAdv.mismatch : ∀ p q : Prop, p ∧ q → q ∧ p := OpnProp.and_swap
