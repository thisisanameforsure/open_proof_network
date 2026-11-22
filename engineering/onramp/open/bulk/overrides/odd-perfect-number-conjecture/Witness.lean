/-! Non-vacuity witness (D-4 step 7): 6 is a perfect number, since 1 + 2 + 3 = 6. -/

theorem witness : ∃ (n : ℕ), Nat.Perfect n :=
  ⟨6, by first | exact ⟨by decide, by norm_num⟩ | exact ⟨by rfl, by norm_num⟩ | exact ⟨by simp [Nat.properDivisors]; decide, by norm_num⟩ | decide⟩
