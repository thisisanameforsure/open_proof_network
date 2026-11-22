/-! Non-vacuity witness (D-4 step 7): n = 5041 exceeds 5040. -/

theorem witness : ∃ (n : ℕ), n > (5040 : ℕ) :=
  ⟨5041, by norm_num⟩
