import Mathlib

theorem hsize_test : ∀ (Qc : ℕ → ℕ → ℚ),
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
                          n ≠ (5 : ℕ) →
                            n ≠ (7 : ℕ) →
                              ((2 : ℕ) ^ (n * (n + (1 : ℕ)) / (2 : ℕ)) * M n * C n) ^ (2 : ℕ) ≤
                                (2 : ℕ) ^ ((3 : ℕ) * n * n) := by
  intro Qc _ Qx _ Aq _ n M hM C hC _ _ _ h5 h7
  subst hM hC
  simp only []
  by_cases hn : n ≤ 12
  · interval_cases n <;> first | omega | decide
  · push_neg at hn
    set h := n / 2 with hh
    have hh2 : 2 * h ≤ n ∧ n ≤ 2 * h + 1 := by omega
    have hE : n * (n + 1) / 2 * 2 = n * (n + 1) := Nat.div_mul_cancel (Nat.even_mul_succ_self n).two_dvd
    have hM' : ∏ m ∈ Finset.Ioc h n, (2 ^ m - 1) ≤ 2 ^ (∑ m ∈ Finset.Ioc h n, m) := by
      rw [← Finset.prod_pow_eq_pow_sum]
      exact Finset.prod_le_prod (fun _ _ => Nat.zero_le _) (fun m _ => Nat.sub_le _ _)
    have hC' : ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) ≤ 2 ^ (∑ j ∈ Finset.range n, (j + 1)) := by
      calc ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) ≤ ∏ j ∈ Finset.Ico 2 n, 2 ^ (j + 1) :=
            Finset.prod_le_prod (fun _ _ => Nat.zero_le _) (fun j _ => Nat.sub_le _ _)
        _ = 2 ^ (∑ j ∈ Finset.Ico 2 n, (j + 1)) := Finset.prod_pow_eq_pow_sum _ _ _
        _ ≤ 2 ^ (∑ j ∈ Finset.range n, (j + 1)) :=
            Nat.pow_le_pow_right (by norm_num) (Finset.sum_le_sum_of_subset (fun j hj => by
              simp only [Finset.mem_Ico] at hj; exact Finset.mem_range.mpr hj.2))
    have h3 := Finset.sum_range_id_mul_two (n + 1)
    have h2 := Finset.sum_range_id_mul_two (h + 1)
    simp only [Nat.add_sub_cancel] at h2 h3
    have hS1 : (∑ m ∈ Finset.Ioc h n, m) * 2 + (h + 1) * h = (n + 1) * n := by
      have hI : Finset.Ioc h n = Finset.Ico (h + 1) (n + 1) := by
        ext m; simp only [Finset.mem_Ioc, Finset.mem_Ico]; omega
      have h1 : (∑ m ∈ Finset.range (h + 1), m) + ∑ m ∈ Finset.Ico (h + 1) (n + 1), m =
          ∑ m ∈ Finset.range (n + 1), m := by
        rw [Finset.range_eq_Ico, Finset.range_eq_Ico]
        exact Finset.sum_Ico_consecutive _ (by omega) (by omega)
      rw [hI]
      linarith
    have hS2 : (∑ j ∈ Finset.range n, (j + 1)) * 2 = (n + 1) * n := by
      have := Finset.sum_range_succ' (fun j => j) n
      simp only [add_zero] at this
      rw [← this]
      exact h3
    have hsq := Nat.mul_le_mul hh2.2 hh2.2
    have h13 := Nat.mul_le_mul_right n hn
    calc _ ≤ (2 ^ (n * (n + 1) / 2) * 2 ^ (∑ m ∈ Finset.Ioc h n, m) * 2 ^ (∑ j ∈ Finset.range n, (j + 1))) ^ 2 := by
          gcongr
      _ = 2 ^ ((n * (n + 1) / 2 + ∑ m ∈ Finset.Ioc h n, m + ∑ j ∈ Finset.range n, (j + 1)) * 2) := by
          rw [← pow_add, ← pow_add, ← pow_mul]
      _ ≤ 2 ^ (3 * n * n) := Nat.pow_le_pow_right (by norm_num) (by nlinarith)
