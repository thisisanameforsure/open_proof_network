/-! Non-vacuity witness (D-4 step 7): a = b = c = 1 are positive. -/

theorem witness : ∃ (a b c : ℕ), 0 < a ∧ 0 < b ∧ 0 < c := ⟨1, 1, 1, Nat.one_pos, Nat.one_pos, Nat.one_pos⟩
