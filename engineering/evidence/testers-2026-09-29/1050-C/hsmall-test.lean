import Mathlib

theorem hsmall_test : ∀ (Qc : ℕ → ℕ → ℚ),
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
            ∀ (n : ℕ) (M : ℕ → ℕ),
              (M = fun (n : ℕ) => ∏ m ∈ Finset.Ioc (n / (2 : ℕ)) n, ((2 : ℕ) ^ m - (1 : ℕ))) →
                ∀ (C : ℕ → ℕ),
                  (C = fun (n : ℕ) => ∏ j ∈ Finset.Ico (2 : ℕ) n, ((2 : ℕ) ^ (j + (1 : ℕ)) - (3 : ℕ))) →
                    (∀ k ≤ n, ∃ (z : ℤ), (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) = Qc n k) →
                      (∀ k ≤ n,
                          ∃ (z : ℤ),
                            (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) =
                              (↑(M n) : ℚ) * ∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) →
                        (∃ (z : ℤ),
                            (↑z : ℚ) =
                              (↑(C n) : ℚ) * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ))) →
                          (n ≠ (5 : ℕ) →
                              n ≠ (7 : ℕ) →
                                ((2 : ℕ) ^ (n * (n + (1 : ℕ)) / (2 : ℕ)) * M n * C n) ^ (2 : ℕ) ≤
                                  (2 : ℕ) ^ ((3 : ℕ) * n * n)) →
                            (n = (5 : ℕ) →
                                ∃ (z : ℤ) (z' : ℤ),
                                  (↑z : ℚ) = (13403586560 : ℚ) * Qx n ∧ (↑z' : ℚ) = (13403586560 : ℚ) * Aq n) ∧
                              (n = (7 : ℕ) →
                                ∃ (z : ℤ) (z' : ℤ),
                                  (↑z : ℚ) = (348621924990976000 : ℚ) * Qx n ∧
                                    (↑z' : ℚ) = (348621924990976000 : ℚ) * Aq n) := by
  intro Qc hQc Qx hQx Aq hAq n M _ C _ _ _ _ _
  subst hQc hQx hAq
  refine ⟨fun h5 => ?_, fun h7 => ?_⟩
  · subst h5
    refine ⟨1338545055613790115, 1380067124193819576, ?_, ?_⟩
    · norm_num [Finset.sum_range_succ, Finset.prod_range_succ]
    · norm_num [Finset.sum_range_succ, Finset.prod_range_succ]
  · subst h7
    refine ⟨653756503247821948956012109840125, 674036225808261890798679141926088, ?_, ?_⟩
    · norm_num [Finset.sum_range_succ, Finset.prod_range_succ]
    · norm_num [Finset.sum_range_succ, Finset.prod_range_succ]
