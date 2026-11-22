/-! Non-vacuity witness (D-4 step 7): 3121 is an odd prime greater than 3119. -/

theorem witness : ∃ (k : ℕ), Nat.Prime k ∧ Odd k ∧ k > (3119 : ℕ) :=
  ⟨3121, by norm_num, ⟨1560, by norm_num⟩, by norm_num⟩
