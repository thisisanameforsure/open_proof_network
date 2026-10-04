/-! F19-AC1: two named haves, one closed by `omega`, one by three tactics with a nested `obtain`
(the `show` is a step of its own, F19-Q4). Lean core only. -/

theorem OpnOutline.steps (a b : Nat) (h : a < b) (p : Nat × Nat) :
    a + 1 ≤ b ∧ p.1 + 0 = p.1 := by
  have h1 : a + 1 ≤ b := by omega
  have key : p.1 + 0 = p.1 := by
    obtain ⟨x, y⟩ := p
    show x + 0 = x
    exact Nat.add_zero x
  exact ⟨h1, key⟩
