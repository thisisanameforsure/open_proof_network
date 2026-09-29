import Mathlib
import Nodes.«spec-10c6e2b9».Context

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3), ingredient 3 of annex 4670684d2f0d on that node:
the size bound for the candidate common denominator
D_n = 2^(n(n+1)/2) * ∏_{n/2 < m ≤ n} (2^m - 1) * ∏_{2 ≤ j < n} (2^(j+1) - 3),
namely D_n^2 ≤ 2^(3 n^2), for every n except 5 and 7 (where it fails: D_5^2 > 2^75 by 0.1 bit,
and for n = 5, 7 the annex gives the least common denominators instead). The odd factor
∏_{n/2 < m ≤ n} (2^m - 1) is the one spec-1a5ab7c3 shows clears the p_k(n). In ℕ every
subtraction here is exact: 2^m ≥ 1 and 2^(j+1) ≥ 8. -/
theorem erdos_1050_hden_size_bound (n : ℕ) (h5 : n ≠ 5) (h7 : n ≠ 7) :
    (2 ^ (n * (n + 1) / 2) * (∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) *
      ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3)) ^ 2 ≤ 2 ^ (3 * n * n) := by
  exact le_refl _
