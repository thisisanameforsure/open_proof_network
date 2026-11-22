/-! Non-vacuity witness (D-4 step 7): n = 1 is positive. -/

theorem witness : ∃ (n : ℕ), n > (0 : ℕ) :=
  ⟨1, Nat.one_pos⟩
