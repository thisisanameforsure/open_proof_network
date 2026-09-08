theorem OpnAdv.wrong_witness : ∀ p q : Prop, p ∧ q → q ∧ p := by
  intro p q h
  exact ⟨h.2, h.1⟩
