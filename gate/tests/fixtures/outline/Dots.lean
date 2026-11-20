/-! F19-T11: a constant written through dot notation (`h.symm`, `n.succ_ne_zero`) is a use of the
constant it resolves to, as one written in full is. Lean core only. -/

theorem OpnOutline.dots (a b n : Nat) (h : a = b) : b = a ∧ Nat.succ n ≠ 0 := by
  have hs : b = a := h.symm
  have hn : Nat.succ n ≠ 0 := n.succ_ne_zero
  exact ⟨hs, hn⟩
