import Mathlib

theorem size_large (n : ℕ) (hn : 10 ≤ n) :
    (2 ^ (n * (n + 1) / 2) * (∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) *
      ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3)) ^ 2 ≤ 2 ^ (3 * n * n) := by
  have hA : (∑ m ∈ Finset.Ioc (n / 2) n, m) * 2 + (n / 2) * (n / 2 + 1) = n * (n + 1) := by
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
