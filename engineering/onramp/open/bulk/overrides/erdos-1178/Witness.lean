/-! Non-vacuity witness (D-4 step 7): r = e = 3 are both at least 3. -/

theorem witness : ∃ (r : ℕ) (e : ℕ), (3 : ℕ) ≤ r ∧ (3 : ℕ) ≤ e := ⟨3, 3, le_refl 3, le_refl 3⟩
