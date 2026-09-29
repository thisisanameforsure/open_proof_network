import Mathlib
import Nodes.«spec-1a5ab7c3».Context

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3), ingredient 2, odd half, of annex 4670684d2f0d
on that node. Every denominator 2^(k - j) - 1 with 1 ≤ k - j ≤ n divides
M_n = ∏_{n/2 < m ≤ n} (2^m - 1), because m has the multiple m * (n / m) in (n/2, n]. Hence M_n
clears the inner sum p_k(n) = ∑_{j ≤ k} Qc n j / (2^(k - j) - 1) of `Aq` in h3 for any integer
coefficients (Qc n j is one by ingredient 1, spec-440db0f9). The j = k term divides by 2^0 - 1 = 0
and is 0 in ℚ, as in h3. The 2-adic half of ingredient 2 (v2(p_k(n)) ≥ k(k-1)/2) is not claimed. -/
theorem erdos_1050_upper_half_mersenne_clears (n k : ℕ) (hk : k ≤ n) (c : ℕ → ℤ) :
    ∃ z : ℤ, (z : ℚ) = (∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ m - 1)) *
      ∑ j ∈ Finset.range (k + 1), (c j : ℚ) / ((2 : ℚ) ^ (k - j) - 1) := by
  sorry
