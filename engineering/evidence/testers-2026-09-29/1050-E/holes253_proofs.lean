import Mathlib

theorem hole_hcint : ∀ (Qc : ℕ → ℕ → ℚ),
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
                        ∃ (z : ℤ),
                          (↑z : ℚ) = (↑(C n) : ℚ) * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ)) := by
  intro Qc hQc Qx hQx Aq hAq n M hM C hC _ _
  subst hC
  show ∃ z : ℤ, (z : ℚ) = ((∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) : ℕ) : ℚ) *
      ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + 1) - 3)
  rw [Finset.mul_sum]
  refine Finset.sum_induction _ (fun q : ℚ => ∃ z : ℤ, (z : ℚ) = q)
    (fun x y ⟨zx, hx⟩ ⟨zy, hy⟩ => ⟨zx + zy, by push_cast; rw [hx, hy]⟩) ⟨0, by simp⟩ ?_
  intro j hj
  have hjn : j < n := Finset.mem_range.mp hj
  rcases Nat.lt_or_ge j 2 with h2 | h2
  · interval_cases j
    · exact ⟨-3 * ((∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) : ℕ) : ℤ), by push_cast; ring⟩
    · exact ⟨3 * ((∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) : ℕ) : ℤ), by push_cast; ring⟩
  · have hmem : j ∈ Finset.Ico 2 n := Finset.mem_Ico.mpr ⟨h2, hjn⟩
    have h8 : 3 ≤ 2 ^ (j + 1) := by
      calc 3 ≤ 2 ^ 2 := by norm_num
        _ ≤ 2 ^ (j + 1) := Nat.pow_le_pow_right (by norm_num) (by omega)
    have hq : ((2 ^ (j + 1) - 3 : ℕ) : ℚ) = (2 : ℚ) ^ (j + 1) - 3 := by
      rw [Nat.cast_sub h8]; push_cast; ring
    have hne : (2 : ℚ) ^ (j + 1) - 3 ≠ 0 := by
      rw [← hq]; exact_mod_cast (by omega : 2 ^ (j + 1) - 3 ≠ 0)
    refine ⟨3 * ((∏ i ∈ (Finset.Ico 2 n).erase j, (2 ^ (i + 1) - 3) : ℕ) : ℤ), ?_⟩
    rw [← Finset.mul_prod_erase _ _ hmem, Nat.cast_mul, hq]
    push_cast
    field_simp

theorem hole_hsize : ∀ (Qc : ℕ → ℕ → ℚ),
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
  intro Qc hQc Qx hQx Aq hAq n M hM C hC _ _ _ h5 h7
  subst hM hC
  show (2 ^ (n * (n + 1) / 2) * (∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) *
      ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3)) ^ 2 ≤ 2 ^ (3 * n * n)
  rcases Nat.lt_or_ge n 10 with hn | hn
  · interval_cases n <;> first | omega | decide
  · have hA : (∑ m ∈ Finset.Ioc (n / 2) n, m) * 2 + (n / 2) * (n / 2 + 1) = n * (n + 1) := by
      have h1 : Finset.Ioc (n / 2) n = Finset.Ico (n / 2 + 1) (n + 1) := by
        ext x; simp only [Finset.mem_Ioc, Finset.mem_Ico]; omega
      rw [h1]
      have h2 := Finset.sum_range_add_sum_Ico (fun m => m) (show n / 2 + 1 ≤ n + 1 by omega)
      have h3 := Finset.sum_range_id_mul_two (n + 1)
      have h4 := Finset.sum_range_id_mul_two (n / 2 + 1)
      simp only [Nat.add_sub_cancel] at h3 h4
      nlinarith [h2, h3, h4]
    have hB : (∑ j ∈ Finset.Ico 2 n, (j + 1)) * 2 + 6 = n * (n + 1) := by
      have h2 := Finset.sum_range_add_sum_Ico (fun j => j + 1) (show 2 ≤ n by omega)
      have h3 := Finset.sum_range_id_mul_two n
      have h5 : ∑ j ∈ Finset.range n, (j + 1) = ∑ j ∈ Finset.range n, j + n := by
        rw [Finset.sum_add_distrib]; simp
      have h6 : ∑ j ∈ Finset.range 2, (j + 1) = 3 := by decide
      rw [h6, h5] at h2
      have h7 : n * (n - 1) + 2 * n = n * (n + 1) := by
        cases n with
        | zero => omega
        | succ k => simp only [Nat.add_sub_cancel]; ring
      nlinarith [h2, h3, h7]
    have hE : n * (n + 1) / 2 * 2 = n * (n + 1) :=
      Nat.div_mul_cancel (Nat.even_mul_succ_self n).two_dvd
    have hP1 : ∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1) ≤ 2 ^ (∑ m ∈ Finset.Ioc (n / 2) n, m) := by
      rw [← Finset.prod_pow_eq_pow_sum]
      exact Finset.prod_le_prod' (fun m _ => Nat.sub_le _ _)
    have hP2 : ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) ≤ 2 ^ (∑ j ∈ Finset.Ico 2 n, (j + 1)) := by
      rw [← Finset.prod_pow_eq_pow_sum]
      exact Finset.prod_le_prod' (fun j _ => Nat.sub_le _ _)
    have hexp : 2 * (n * (n + 1) / 2 + ∑ m ∈ Finset.Ioc (n / 2) n, m + ∑ j ∈ Finset.Ico 2 n, (j + 1))
        ≤ 3 * n * n := by
      have hh1 : 2 * (n / 2) ≤ n := Nat.mul_div_le n 2
      have hh2 : n ≤ 2 * (n / 2) + 1 := by omega
      have hh3 : 5 ≤ n / 2 := by omega
      nlinarith [hA, hB, hE, hh1, hh2, hh3]
    calc (2 ^ (n * (n + 1) / 2) * (∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) *
          ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3)) ^ 2
        ≤ (2 ^ (n * (n + 1) / 2) * 2 ^ (∑ m ∈ Finset.Ioc (n / 2) n, m) *
            2 ^ (∑ j ∈ Finset.Ico 2 n, (j + 1))) ^ 2 :=
          Nat.pow_le_pow_left (Nat.mul_le_mul (Nat.mul_le_mul le_rfl hP1) hP2) 2
      _ = 2 ^ (2 * (n * (n + 1) / 2 + ∑ m ∈ Finset.Ioc (n / 2) n, m + ∑ j ∈ Finset.Ico 2 n, (j + 1))) := by
          rw [← pow_add, ← pow_add, ← pow_mul]; ring_nf
      _ ≤ 2 ^ (3 * n * n) := Nat.pow_le_pow_right (by norm_num) hexp

theorem hole_hsmall : ∀ (Qc : ℕ → ℕ → ℚ),
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
  intro Qc hQc Qx hQx Aq hAq n M hM C hC _ _ _ _
  subst hQc hQx hAq
  refine ⟨fun h5 => ?_, fun h7 => ?_⟩
  · subst h5
    refine ⟨1338545055613790115, 1380067124193819576, ?_, ?_⟩
    · simp only [Finset.sum_range_succ, Finset.prod_range_succ, Finset.sum_range_zero, Finset.prod_range_zero]
      norm_num
    · simp only [Finset.sum_range_succ, Finset.prod_range_succ, Finset.sum_range_zero, Finset.prod_range_zero]
      norm_num
  · subst h7
    refine ⟨653756503247821948956012109840125, 674036225808261890798679141926088, ?_, ?_⟩
    · simp only [Finset.sum_range_succ, Finset.prod_range_succ, Finset.sum_range_zero, Finset.prod_range_zero]
      norm_num
    · simp only [Finset.sum_range_succ, Finset.prod_range_succ, Finset.sum_range_zero, Finset.prod_range_zero]
      norm_num

