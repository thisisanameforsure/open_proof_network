/-! Non-vacuity witness (D-4 step 7): m = 1 and w = 0 satisfy 1 ≤ m and w ≤ 4m. -/

theorem witness : ∃ (m : ℕ) (w : ℕ), (1 : ℕ) ≤ m ∧ w ≤ (4 : ℕ) * m := ⟨1, 0, le_refl 1, by norm_num⟩
