/-! Non-vacuity witness (D-4 step 7): p = 2 is a prime in ℕ+. -/

theorem witness : ∃ (p : ℕ+), p.Prime := ⟨2, Nat.prime_two⟩
