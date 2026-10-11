import Mathlib

theorem size_small : ∀ n : ℕ, n ≤ 9 → n ≠ 5 → n ≠ 7 →
    (2 ^ (n * (n + 1) / 2) * (∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) *
      ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3)) ^ 2 ≤ 2 ^ (3 * n * n) := by
  intro n hn h5 h7
  interval_cases n <;> first | omega | decide

theorem sums (n : ℕ) :
    (∑ m ∈ Finset.Ioc (n / 2) n, m) * 2 + (n / 2) * (n / 2 + 1) = n * (n + 1) := by
  have h1 : Finset.Ioc (n / 2) n = Finset.Ico (n / 2 + 1) (n + 1) := by
    ext x; simp only [Finset.mem_Ioc, Finset.mem_Ico]; omega
  rw [h1]
  have h2 := Finset.sum_range_add_sum_Ico (fun m => m) (show n / 2 + 1 ≤ n + 1 by omega)
  have h3 := Finset.sum_range_id_mul_two (n + 1)
  have h4 := Finset.sum_range_id_mul_two (n / 2 + 1)
  simp only [Nat.add_sub_cancel] at h3 h4
  nlinarith [h2, h3, h4]
