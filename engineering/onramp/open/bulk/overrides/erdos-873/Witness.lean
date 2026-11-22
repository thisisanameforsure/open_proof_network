/-! Non-vacuity witness (D-4 step 7): a n = n + 1 is strictly increasing with a 0 = 1 > 0, and ε = 1 > 0. -/

theorem witness : ∃ (a : ℕ → ℕ), ∃ ε > (0 : ℝ), (0 : ℕ) < a (0 : ℕ) ∧ StrictMono a :=
  ⟨fun n => n + 1, 1, one_pos, Nat.one_pos, fun _ _ h => Nat.add_lt_add_right h 1⟩
