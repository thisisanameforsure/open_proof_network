/-! Non-vacuity witness (D-4 step 7): m = n = 1 are positive. -/

theorem witness : ∃ (m n : ℕ), m > 0 ∧ n > 0 := ⟨1, 1, Nat.one_pos, Nat.one_pos⟩
