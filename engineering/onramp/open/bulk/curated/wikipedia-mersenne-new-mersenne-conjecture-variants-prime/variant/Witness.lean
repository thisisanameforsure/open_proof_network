/-! Non-vacuity witness (D-4 step 7): p = 3 is an odd prime. -/

theorem witness : ∃ (p : ℕ), Nat.Prime p ∧ Odd p := ⟨3, Nat.prime_three, by decide⟩
