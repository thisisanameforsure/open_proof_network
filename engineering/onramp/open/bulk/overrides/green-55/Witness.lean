/-! Non-vacuity witness (D-4 step 7): the prime p = 3, which is not 2. -/

theorem witness : ∃ (p : ℕ), Fact (Nat.Prime p) ∧ p ≠ 2 :=
  ⟨3, ⟨Nat.prime_three⟩, by norm_num⟩
