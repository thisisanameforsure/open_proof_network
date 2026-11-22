/-! Non-vacuity witness (D-4 step 7): 35 = 5 · 7 is a crystal with components (5, 7), taken twice. -/

theorem witness : ∃ (n : ℕ) (a : ℕ) (b : ℕ) (c : ℕ) (d : ℕ), IsCrystalWithComponents n a b ∧ IsCrystalWithComponents n c d :=
  ⟨35, 5, 7, 5, 7, by norm_num [IsCrystalWithComponents], by norm_num [IsCrystalWithComponents]⟩
