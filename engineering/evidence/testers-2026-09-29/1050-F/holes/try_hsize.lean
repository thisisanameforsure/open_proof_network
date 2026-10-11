import Mathlib

theorem guess_hsize : ∀ (Qc : ℕ → ℕ → ℚ),
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
            ∀ (n : ℕ) (M : ℕ → ℕ), M = (fun n => ∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) →
              ∀ (C : ℕ → ℕ), C = (fun n => ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3)) →
                (∀ k ≤ n, ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (k * (k - 1) / 2) = Qc n k) →
                (∀ k ≤ n, ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (k * (k - 1) / 2) =
                    (M n : ℚ) * ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1)) →
                (∃ z : ℤ, (z : ℚ) = (C n : ℚ) * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + 1) - 3)) →
                n ≠ 5 → n ≠ 7 → (2 ^ (n * (n + 1) / 2) * M n * C n) ^ 2 ≤ 2 ^ (3 * n * n) := by
  have key : ∀ n : ℕ, n ≠ 5 → n ≠ 7 →
      (2 ^ (n * (n + 1) / 2) * (∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) *
        ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3)) ^ 2 ≤ 2 ^ (3 * n * n) := by
    intro n h5 h7
    rcases Nat.lt_or_ge n 10 with hn | hn
    · interval_cases n <;> first | exact absurd rfl h5 | exact absurd rfl h7 | decide
    · -- Gauss sums over the two index ranges
      have gauss1 : ∀ a b : ℕ, a ≤ b → (∑ m ∈ Finset.Ioc a b, m) * 2 + a * (a + 1) = b * (b + 1) := by
        intro a b hab
        induction b, hab using Nat.le_induction with
        | base => simp
        | succ b hab ih =>
          rw [Finset.sum_Ioc_succ_top hab]
          nlinarith [ih]
      have gauss2 : ∀ b : ℕ, 2 ≤ b → (∑ j ∈ Finset.Ico 2 b, (j + 1)) * 2 + 6 = b * (b + 1) := by
        intro b hb
        induction b, hb using Nat.le_induction with
        | base => simp
        | succ b hb ih =>
          rw [Finset.sum_Ico_succ_top hb]
          nlinarith [ih]
      have hP1 : ∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1) ≤ 2 ^ (∑ m ∈ Finset.Ioc (n / 2) n, m) := by
        rw [← Finset.prod_pow_eq_pow_sum]
        exact Finset.prod_le_prod' (fun m _ => Nat.sub_le _ _)
      have hP2 : ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) ≤ 2 ^ (∑ j ∈ Finset.Ico 2 n, (j + 1)) := by
        rw [← Finset.prod_pow_eq_pow_sum]
        exact Finset.prod_le_prod' (fun j _ => Nat.sub_le _ _)
      have hS1 := gauss1 (n / 2) n (Nat.div_le_self n 2)
      have hS2 := gauss2 n (by omega)
      have hT : n * (n + 1) / 2 * 2 = n * (n + 1) :=
        Nat.div_mul_cancel (Nat.even_mul_succ_self n).two_dvd
      have hh1 : n / 2 * 2 ≤ n := Nat.div_mul_le_self n 2
      have hh2 : n < n / 2 * 2 + 2 := by omega
      have hh5 : 5 ≤ n / 2 := by omega
      have hexp : 2 * (n * (n + 1) / 2 + ∑ m ∈ Finset.Ioc (n / 2) n, m + ∑ j ∈ Finset.Ico 2 n, (j + 1))
          ≤ 3 * n * n := by
        nlinarith [hS1, hS2, hT, hh1, hh2, hh5]
      calc (2 ^ (n * (n + 1) / 2) * (∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) *
            ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3)) ^ 2
          ≤ (2 ^ (n * (n + 1) / 2) * 2 ^ (∑ m ∈ Finset.Ioc (n / 2) n, m) *
              2 ^ (∑ j ∈ Finset.Ico 2 n, (j + 1))) ^ 2 :=
            Nat.pow_le_pow_left (Nat.mul_le_mul (Nat.mul_le_mul le_rfl hP1) hP2) 2
        _ = 2 ^ (2 * (n * (n + 1) / 2 + ∑ m ∈ Finset.Ioc (n / 2) n, m +
              ∑ j ∈ Finset.Ico 2 n, (j + 1))) := by
            rw [← pow_add, ← pow_add, ← pow_mul, mul_comm]
        _ ≤ 2 ^ (3 * n * n) := Nat.pow_le_pow_right (by norm_num) hexp
  intros
  subst_vars
  exact key _ (by assumption) (by assumption)
