import Mathlib

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3), the Qx half of its integrality claim, from
annex 4670684d2f0d on that node: with `Qc` and `Qx` exactly as in h3, 2^(n(n+1)/2) * Qx n is an
integer. Each Qc n k is (-1)^k 2^(k(k-1)/2) times two Gaussian binomials at q = 2, integers by
spec-440db0f9 (the second is [2n-k, n]_2), so its term Qc n k (3/2^n)^k has 2-denominator at most
2^(nk - k(k-1)/2) ≤ 2^(n(n+1)/2), since n(n+1)/2 + k(k-1)/2 - nk = (n-k)(n-k+1)/2 ≥ 0. Hence
d = 2^(n(n+1)/2) times any odd factor clears Qx n; with spec-1a5ab7c3 this leaves only the
2-adic part of Aq n (the annex's v2(p_k(n)) ≥ k(k-1)/2) open for h3's integrality. -/
theorem erdos_1050_hden_Qx_two_power : ∀ (Qc : ℕ → ℕ → ℚ),
    (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - 1) / 2) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - k - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) →
    ∀ (Qx : ℕ → ℚ),
      (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + 1), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) →
        ∀ (n : ℕ), ∃ z : ℤ, (z : ℚ) = (2 : ℚ) ^ (n * (n + 1) / 2) * Qx n := by
  sorry
