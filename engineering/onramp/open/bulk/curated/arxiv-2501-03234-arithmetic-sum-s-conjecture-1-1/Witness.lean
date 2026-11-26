/-! Non-vacuity witness (D-4 step 7): k = 3 is an odd prime. -/

theorem witness : ∃ (k : ℕ), k.Prime ∧ Odd k := ⟨3, Nat.prime_three, by decide⟩
