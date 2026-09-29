import Mathlib

/-- erdos-1050, hole `hpint` of the skeleton on erdos-1050--h1-v2--h3 (graph PR #253): a closed form
for the Padé numerator coefficient p_k = ∑_{j<k} Qc n j / (2^(k-j) - 1), k ≤ n (the j = k term is
0 in ℚ). It is the regular part at z = 2^k of the rational function ∑_j Qc n j / (z/2^j - 1), whose
product form is spec-f2b55478's (a declared dependency: it holds at z = 2^m for every m > n, hence as
rational functions of z), corrected for the terms j > k that p_k leaves out. Every term on the
right has 2-adic valuation at least k(k-1)/2, which is the 2-adic half of `hpint`. Checked exactly
(Python fractions) for 1 ≤ n ≤ 13 and every k ≤ n, and with 2 replaced by 3 and 5. -/
theorem erdos_1050_pade_numerator_closed_form : ∀ (Qc : ℕ → ℕ → ℚ),
    (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - 1) / 2) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - k - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) →
    ∀ n k : ℕ, k ≤ n →
      ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1) =
        Qc n k * (∑ i ∈ Finset.range n, 1 / (1 - (2 : ℚ) ^ (n + 1 + i - k)) -
            ∑ b ∈ Finset.range k, (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) -
            ∑ b ∈ Finset.range (n - k), 1 / (1 - (2 : ℚ) ^ (b + 1))) +
          ∑ b ∈ Finset.range (n - k), Qc n (k + b + 1) * (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := by
  sorry
