/-! Non-vacuity witness (D-4 step 7): n = 4210 is even and exceeds 4208. -/

theorem witness : ∃ (n : ℕ), (4208 : ℕ) < n ∧ Even n := ⟨4210, by norm_num, ⟨2105, by norm_num⟩⟩
