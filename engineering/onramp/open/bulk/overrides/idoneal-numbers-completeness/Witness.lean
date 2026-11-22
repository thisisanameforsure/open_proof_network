/-! Non-vacuity witness (D-4 step 7): 1 is idoneal, since ab + bc + ac ≥ 2 + 6 + 3 for 0 < a < b < c. -/

theorem witness : ∃ (n : ℕ), Idoneal.IsIdoneal n :=
  ⟨1, one_pos, fun ⟨a, b, c, ha, hab, hbc, h⟩ => by
    have hb : 2 ≤ b := by omega
    have hc : 3 ≤ c := by omega
    nlinarith [Nat.mul_le_mul hb hc, Nat.mul_le_mul ha hb]⟩
