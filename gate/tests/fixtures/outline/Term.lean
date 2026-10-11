/-! F19-AC6: a term-mode proof is one `term` step. -/

theorem OpnOutline.term (n : Nat) : n + 0 = n :=
  Nat.add_zero n
