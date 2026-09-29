import Mathlib

theorem hcint_core (n : ℕ) : ∃ z : ℤ, (z : ℚ) =
    ((∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) : ℕ) : ℚ) *
      ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + 1) - 3) := by
  rw [Finset.mul_sum]
  refine Finset.sum_induction _ (fun q : ℚ => ∃ z : ℤ, (z : ℚ) = q)
    (fun x y ⟨zx, hx⟩ ⟨zy, hy⟩ => ⟨zx + zy, by push_cast; rw [hx, hy]⟩) ⟨0, by simp⟩ ?_
  intro j hj
  have hjn : j < n := Finset.mem_range.mp hj
  rcases Nat.lt_or_ge j 2 with h2 | h2
  · interval_cases j
    · exact ⟨-3 * ((∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) : ℕ) : ℤ), by push_cast; ring⟩
    · exact ⟨3 * ((∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) : ℕ) : ℤ), by push_cast; ring⟩
  · have hmem : j ∈ Finset.Ico 2 n := Finset.mem_Ico.mpr ⟨h2, hjn⟩
    have h8 : 3 ≤ 2 ^ (j + 1) := by
      calc 3 ≤ 2 ^ 2 := by norm_num
        _ ≤ 2 ^ (j + 1) := Nat.pow_le_pow_right (by norm_num) (by omega)
    have hq : ((2 ^ (j + 1) - 3 : ℕ) : ℚ) = (2 : ℚ) ^ (j + 1) - 3 := by
      rw [Nat.cast_sub h8]; push_cast; ring
    have hne : (2 : ℚ) ^ (j + 1) - 3 ≠ 0 := by
      rw [← hq]; exact_mod_cast (by omega : 2 ^ (j + 1) - 3 ≠ 0)
    refine ⟨3 * ((∏ i ∈ (Finset.Ico 2 n).erase j, (2 ^ (i + 1) - 3) : ℕ) : ℤ), ?_⟩
    rw [← Finset.mul_prod_erase _ _ hmem, Nat.cast_mul, hq]
    push_cast
    field_simp
