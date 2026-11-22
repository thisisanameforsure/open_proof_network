/-! Non-vacuity witness (D-4 step 7): n = 9 is odd and exceeds 8. -/

theorem witness : ∃ (n : ℕ), 8 < n ∧ Odd n := ⟨9, by norm_num, ⟨4, by norm_num⟩⟩
