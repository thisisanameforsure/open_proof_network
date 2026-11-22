/-! Non-vacuity witness (D-4 step 7): the prime 3 is a prime other than 2. -/

theorem witness : ∃ (p : ℕ), Nat.Prime p ∧ p ≠ (2 : ℕ) := ⟨3, Nat.prime_three, by norm_num⟩
