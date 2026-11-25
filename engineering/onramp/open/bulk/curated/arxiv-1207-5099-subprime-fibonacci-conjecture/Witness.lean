/-! Non-vacuity witness (D-4 step 7): x = 1 and y = 1 are positive naturals, so the hypotheses
`0 < x` and `0 < y` can be met. -/

theorem witness : ∃ (x : ℕ) (y : ℕ), 0 < x ∧ 0 < y := ⟨1, 1, Nat.one_pos, Nat.one_pos⟩
