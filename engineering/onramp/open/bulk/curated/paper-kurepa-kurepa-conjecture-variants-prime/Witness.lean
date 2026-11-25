/-! Non-vacuity witness (D-4 step 7): p = 3 satisfies 2 < p and is prime. -/

theorem witness : ∃ (p : ℕ), 2 < p ∧ Nat.Prime p := ⟨3, by norm_num, Nat.prime_three⟩
