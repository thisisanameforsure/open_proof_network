import Mathlib
import Nodes.«spec-e8da19d1».Context

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3): the last term of `Aq` in h3 is
Qx n * c_n with c_n = ∑_{j < n} 3 / (2^(j+1) - 3). Its denominators are 2 - 3 = -1, 4 - 3 = 1 and
2^(j+1) - 3 for 2 ≤ j < n, so the factor ∏_{2 ≤ j < n} (2^(j+1) - 3) of the annex's candidate D_n
(annex 4670684d2f0d on h3; size bound spec-10c6e2b9) clears c_n. With spec-938d7dd3 (the power of 2
clears Qx n) this settles the Qx n * c_n part of D_n * Aq n. -/
theorem erdos_1050_hden_cn_clears (n : ℕ) :
    ∃ z : ℤ, (z : ℚ) = (∏ j ∈ Finset.Ico 2 n, ((2 : ℚ) ^ (j + 1) - 3)) *
      ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + 1) - 3) := by
  have hint : ∀ j ∈ Finset.range n, ∃ z : ℤ,
      (z : ℚ) = (∏ i ∈ Finset.Ico 2 n, ((2 : ℚ) ^ (i + 1) - 3)) * ((3 : ℚ) / ((2 : ℚ) ^ (j + 1) - 3)) := by
    intro j hj
    by_cases h2 : j < 2
    · have hj' : j = 0 ∨ j = 1 := by omega
      rcases hj' with rfl | rfl
      · refine ⟨-3 * ∏ i ∈ Finset.Ico 2 n, ((2 : ℤ) ^ (i + 1) - 3), ?_⟩
        have e : (3 : ℚ) / ((2 : ℚ) ^ (0 + 1) - 3) = -3 := by norm_num
        rw [e]
        push_cast
        ring
      · refine ⟨3 * ∏ i ∈ Finset.Ico 2 n, ((2 : ℤ) ^ (i + 1) - 3), ?_⟩
        have e : (3 : ℚ) / ((2 : ℚ) ^ (1 + 1) - 3) = 3 := by norm_num
        rw [e]
        push_cast
        ring
    · have hmem : j ∈ Finset.Ico 2 n := Finset.mem_Ico.mpr ⟨by omega, Finset.mem_range.mp hj⟩
      have hne : ((2 : ℚ) ^ (j + 1) - 3) ≠ 0 := by
        have h8 : (8 : ℚ) ≤ 2 ^ (j + 1) := by
          calc (8 : ℚ) = 2 ^ 3 := by norm_num
            _ ≤ 2 ^ (j + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
        linarith
      refine ⟨3 * ∏ i ∈ (Finset.Ico 2 n).erase j, ((2 : ℤ) ^ (i + 1) - 3), ?_⟩
      rw [← Finset.mul_prod_erase _ _ hmem]
      push_cast
      field_simp
  choose! g hg using hint
  refine ⟨∑ j ∈ Finset.range n, g j, ?_⟩
  push_cast
  rw [Finset.mul_sum]
  exact Finset.sum_congr rfl hg
