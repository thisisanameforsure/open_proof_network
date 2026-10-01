import Mathlib

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3): the last term of `Aq` in h3 is
Qx n * c_n with c_n = ∑_{j < n} 3 / (2^(j+1) - 3). Its denominators are 2 - 3 = -1, 4 - 3 = 1 and
2^(j+1) - 3 for 2 ≤ j < n, so the factor ∏_{2 ≤ j < n} (2^(j+1) - 3) of the annex's candidate D_n
(annex 4670684d2f0d on h3; size bound spec-10c6e2b9) clears c_n. With spec-938d7dd3 (the power of 2
clears Qx n) this settles the Qx n * c_n part of D_n * Aq n. -/
theorem erdos_1050_hden_cn_clears (n : ℕ) :
    ∃ z : ℤ, (z : ℚ) = (∏ j ∈ Finset.Ico 2 n, ((2 : ℚ) ^ (j + 1) - 3)) *
      ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + 1) - 3) := by
  sorry
