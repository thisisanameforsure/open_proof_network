/-! Non-vacuity witness (D-4 step 7): p = 3 is an odd prime, with x = y = 0. -/

theorem witness : ∃ (p : ℕ) (x : ℤ) (y : ℤ), Nat.Prime p ∧ Odd p :=
  ⟨3, 0, 0, by norm_num, ⟨1, by norm_num⟩⟩
