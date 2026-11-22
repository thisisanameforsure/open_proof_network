/-! Non-vacuity witness (D-4 step 7): n = 7 is odd and exceeds 6. -/

theorem witness : ∃ (n : ℕ), (6 : ℕ) < n ∧ Odd n := ⟨7, by norm_num, ⟨3, rfl⟩⟩
