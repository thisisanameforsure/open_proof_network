/-! Non-vacuity witness (D-4 step 7): k = 7, an odd prime greater than 5. -/

theorem witness : ∃ (k : ℕ), Nat.Prime k ∧ Odd k ∧ k > 5 :=
  ⟨7, by norm_num, ⟨3, rfl⟩, by norm_num⟩
