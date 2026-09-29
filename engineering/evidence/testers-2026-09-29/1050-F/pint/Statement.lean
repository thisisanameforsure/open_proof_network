import Mathlib

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3): the 2-adic crux of annex 4670684d2f0d
(its ingredient 2), in the form of the hole `hpint` of the skeleton in graph PR #253. With `Qc` as
in h3 and each Qc n k (k ≤ n) equal to 2^(k(k-1)/2) times an integer (the hole `hQcint`; true by
spec-440db0f9), M_n * p_k(n) is 2^(k(k-1)/2) times an integer, where
M_n = ∏_{n/2 < m ≤ n} (2^m - 1) and p_k(n) = ∑_{j ≤ k} Qc n j / (2^(k-j) - 1). Proof idea: the
partial fractions ∑_{j ≤ n} Qc n j 2^j / (z - 2^j) = ∏_{m=n+1}^{2n} (z - 2^m) / ∏_{j ≤ n} (z - 2^j)
(Lagrange at the nodes 2^j), whose finite part at z = 2^k writes p_k with odd denominators and
every term of 2-adic valuation at least k(k-1)/2; spec-1a5ab7c3's argument clears the odd part. -/
theorem erdos_1050_hden_pint : ∀ (Qc : ℕ → ℕ → ℚ),
  (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) →
    ∀ (n : ℕ), (∀ k ≤ n, ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (k * (k - 1) / 2) = Qc n k) →
      ∀ k ≤ n, ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (k * (k - 1) / 2) =
        ((∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1) : ℕ) : ℚ) *
          ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1) := by
  sorry
