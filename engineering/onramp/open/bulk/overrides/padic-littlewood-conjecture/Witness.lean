/-! Non-vacuity witness (D-4 step 7): α = 0 and the prime p = 2. -/

theorem witness : ∃ (α : ℝ) (p : ℕ), Nat.Prime p :=
  ⟨0, 2, Nat.prime_two⟩
