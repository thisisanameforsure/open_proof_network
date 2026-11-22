/-! Non-vacuity witness (D-4 step 7): k = 239 is an odd prime greater than 233. -/

theorem witness : ∃ (k : ℕ), Nat.Prime k ∧ Odd k ∧ k > (233 : ℕ) :=
  ⟨239, by norm_num, ⟨119, by norm_num⟩, by norm_num⟩
