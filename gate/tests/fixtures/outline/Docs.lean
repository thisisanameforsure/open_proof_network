/-! F19-AC4 in Lean core: a step that uses two core constants, one with a docstring and one
without. Core has no cross-reference attribute, so no constant has a tag. -/

theorem OpnOutline.docs (p q : Prop) (hq : q) (n : Nat) : (q ∨ p) ∧ n + 0 = n := by
  have h : q ∨ p := Or.inl hq
  have e : n + 0 = n := Nat.add_zero n
  exact ⟨h, e⟩
