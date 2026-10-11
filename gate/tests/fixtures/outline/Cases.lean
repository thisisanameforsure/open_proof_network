/-! F22-T14: case branches report the hypotheses their split introduced, and a proof's trailing
closing tactics are a step of their own (`close`). Lean core only. -/

theorem OpnOutline.split (p q r : Prop) (h : p ∨ q) (hp : p → r) (hq : q → r) : r := by
  rcases h with a | b
  · exact hp a
  · exact hq b

theorem OpnOutline.alts (p q r : Prop) (h : p ∨ q) (hp : p → r) (hq : q → r) : r := by
  cases h with
  | inl a => exact hp a
  | inr b => exact hq b

theorem OpnOutline.named (p q r : Prop) (h : p ∨ q) (hp : p → r) (hq : q → r) : r := by
  cases h
  case inl a => exact hp a
  case inr b => exact hq b

theorem OpnOutline.closing (n : Nat) : n + 0 = n ∧ 0 + n = n := by
  have h : n + 0 = n := Nat.add_zero n
  refine ⟨h, ?_⟩
  exact Nat.zero_add n

theorem OpnOutline.onlyClose (n : Nat) : n + 0 = n := by
  exact Nat.add_zero n
