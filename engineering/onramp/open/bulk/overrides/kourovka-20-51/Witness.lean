/-! Non-vacuity witness (D-4 step 7): t = 5 is odd and exceeds 3. -/

theorem witness : ∃ (t : ℕ), t > (3 : ℕ) ∧ Odd t := ⟨5, by norm_num, ⟨2, rfl⟩⟩
