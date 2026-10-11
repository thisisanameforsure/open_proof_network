import Mathlib

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3), ingredient 3's exceptional cases (annex
4670684d2f0d on that node): for n = 5 and n = 7 the annex's candidate D_n is too large
(spec-10c6e2b9 excludes them), but the least common denominators d_5 = 13403586560 and
d_7 = 348621924990976000 of Qx n and Aq n satisfy h3's conclusion (d_5^2 < 2^68 ≤ 2^75,
d_7^2 < 2^117 ≤ 2^147). `Qc`, `Qx`, `Aq` and the conclusion are h3's, verbatim. -/
theorem erdos_1050_hden_n5_n7 : ∀ (Qc : ℕ → ℕ → ℚ),
  (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) →
    ∀ (Qx : ℕ → ℚ),
      (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) →
        ∀ (Aq : ℕ → ℚ),
          (Aq = fun (n : ℕ) =>
              ∑ k ∈ Finset.range (n + (1 : ℕ)),
                  (∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) *
                    ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
                Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ))) →
            ∀ (n : ℕ), n = 5 ∨ n = 7 →
              ∃ (d : ℕ),
                (0 : ℕ) < d ∧
                  (↑d : ℝ) ^ (2 : ℕ) ≤ (2 : ℝ) ^ ((3 : ℕ) * n * n) ∧
                    (∃ (z : ℤ), (↑z : ℚ) = (↑d : ℚ) * Qx n) ∧ ∃ (z : ℤ), (↑z : ℚ) = (↑d : ℚ) * Aq n := by
  sorry
