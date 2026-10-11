import Mathlib
import Nodes.«spec-eb1219eb».Context

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3), the two exceptional cases n = 5 and n = 7.
With Qc, Qx, Aq bound exactly as in that hole, some d > 0 with d^2 ≤ 2^(3n^2) clears both Qx n and
Aq n. Annex 4670684d2f0d's candidate D_n misses the size bound at n = 5 and n = 7 (spec-10c6e2b9
excludes them); the least common denominators d_5 = 13403586560 and d_7 = 348621924990976000
satisfy it. Together with the general case this gives h3 for every n. -/
theorem erdos_1050_hden_small_cases : ∀ (Qc : ℕ → ℕ → ℚ),
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
            ∀ (n : ℕ), (n = 5 ∨ n = 7) →
              ∃ (d : ℕ),
                (0 : ℕ) < d ∧
                  (↑d : ℝ) ^ (2 : ℕ) ≤ (2 : ℝ) ^ ((3 : ℕ) * n * n) ∧
                    (∃ (z : ℤ), (↑z : ℚ) = (↑d : ℚ) * Qx n) ∧ ∃ (z : ℤ), (↑z : ℚ) = (↑d : ℚ) * Aq n := by
  intro Qc hQc Qx hQx Aq hAq n hn
  subst hQc hQx hAq
  rcases hn with rfl | rfl
  · refine ⟨13403586560, by norm_num, by norm_num, ⟨1338545055613790115, ?_⟩,
      ⟨1380067124193819576, ?_⟩⟩
    · simp only [Finset.sum_range_succ, Finset.prod_range_succ, Finset.sum_range_zero,
        Finset.prod_range_zero]
      norm_num
    · simp only [Finset.sum_range_succ, Finset.prod_range_succ, Finset.sum_range_zero,
        Finset.prod_range_zero]
      norm_num
  · refine ⟨348621924990976000, by norm_num, by norm_num, ⟨653756503247821948956012109840125, ?_⟩,
      ⟨674036225808261890798679141926088, ?_⟩⟩
    · simp only [Finset.sum_range_succ, Finset.prod_range_succ, Finset.sum_range_zero,
        Finset.prod_range_zero]
      norm_num
    · simp only [Finset.sum_range_succ, Finset.prod_range_succ, Finset.sum_range_zero,
        Finset.prod_range_zero]
      norm_num
