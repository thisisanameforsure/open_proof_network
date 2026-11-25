/-! Non-vacuity witness (D-4 step 7): a = 2 is not a square integer and is not -1. -/

theorem witness : ∃ (a : ℤ), ¬IsSquare a ∧ a ≠ -1 := by
  refine ⟨2, ?_, by norm_num⟩
  rintro ⟨r, hr⟩
  have h1 : r.natAbs * r.natAbs = 2 := by
    have := congrArg Int.natAbs hr
    simpa [Int.natAbs_mul] using this.symm
  obtain ⟨k, hk⟩ : ∃ k, r.natAbs = k := ⟨_, rfl⟩
  rw [hk] at h1
  have : k ≤ 2 := by nlinarith
  interval_cases k <;> omega
