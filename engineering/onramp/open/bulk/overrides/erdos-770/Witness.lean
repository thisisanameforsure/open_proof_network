/-! Non-vacuity witness (D-4 step 7): p = 2 is prime. -/

theorem witness : ∃ (p : ℕ), Nat.Prime p := ⟨2, Nat.prime_two⟩
