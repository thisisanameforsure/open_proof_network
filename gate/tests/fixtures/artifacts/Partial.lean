/-! A partial proof (D-12 #5): the assembly holds, two named holes stay open. -/

theorem OpnProp.and_swap : ∀ p q : Prop, p ∧ q → q ∧ p := by
  intro p q h
  have right : q := sorry
  have left : p := sorry
  exact ⟨right, left⟩
