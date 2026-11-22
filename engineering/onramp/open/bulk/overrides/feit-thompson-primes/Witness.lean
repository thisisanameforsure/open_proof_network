/-! Non-vacuity witness (D-4 step 7): the primes p = 2 and q = 3 with p < q. -/

theorem witness : ∃ (p : ℕ) (q : ℕ), Nat.Prime p ∧ Nat.Prime q ∧ p < q :=
  ⟨2, 3, Nat.prime_two, Nat.prime_three, by norm_num⟩
