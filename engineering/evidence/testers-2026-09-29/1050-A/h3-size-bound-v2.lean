import Mathlib

theorem boundtest (n : ℕ) :
    ((2 ^ (n * (n + 1) / 2) * (if n = 5 then 409045 else if n = 7 then 1298717875 else
          (∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) * ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) : ℕ) : ℕ) : ℝ) ^ 2 ≤
      (2 : ℝ) ^ (3 * n * n) := by
  have key : (2 ^ (n * (n + 1) / 2) * (if n = 5 then 409045 else if n = 7 then 1298717875 else
          (∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) * ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) : ℕ)) ^ 2 ≤
      2 ^ (3 * n * n) := by
    rcases (show n ≤ 9 ∨ 10 ≤ n by omega) with hn | hn
    · revert n
      decide +kernel
    · rw [if_neg (by omega), if_neg (by omega)]
      have hP1 : ∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1) ≤ 2 ^ (∑ m ∈ Finset.Ioc (n / 2) n, m) := by
        rw [← Finset.prod_pow_eq_pow_sum]
        exact Finset.prod_le_prod' (fun m _ => Nat.sub_le _ _)
      have hP2 : ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) ≤ 2 ^ (∑ j ∈ Finset.Ico 2 n, (j + 1)) := by
        rw [← Finset.prod_pow_eq_pow_sum]
        exact Finset.prod_le_prod' (fun m _ => Nat.sub_le _ _)
      obtain ⟨c, hc⟩ : ∃ c, n = n / 2 + c + 1 := ⟨n - n / 2 - 1, by omega⟩
      obtain ⟨d, hd⟩ : ∃ d, n = d + 3 := ⟨n - 3, by omega⟩
      have hS1 : (∑ m ∈ Finset.Ioc (n / 2) n, m) * 2 = 2 * (c + 1) * (n / 2 + 1) + (c + 1) * c := by
        have e : Finset.Ioc (n / 2) n = Finset.Ico (n / 2 + 1) (n + 1) := by
          ext x; simp only [Finset.mem_Ioc, Finset.mem_Ico]; omega
        rw [e, Finset.sum_Ico_eq_sum_range, show n + 1 - (n / 2 + 1) = c + 1 by omega,
          Finset.sum_add_distrib, Finset.sum_const, Finset.card_range, smul_eq_mul, add_mul,
          Finset.sum_range_id_mul_two]
        simp only [Nat.add_sub_cancel]
        ring
      have hS2 : (∑ j ∈ Finset.Ico 2 n, (j + 1)) * 2 = 6 * (d + 1) + (d + 1) * d := by
        rw [Finset.sum_Ico_eq_sum_range, show n - 2 = d + 1 by omega]
        have : ∀ k ∈ Finset.range (d + 1), 2 + k + 1 = 3 + k := fun k _ => by omega
        rw [Finset.sum_congr rfl this, Finset.sum_add_distrib, Finset.sum_const, Finset.card_range,
          smul_eq_mul, add_mul, Finset.sum_range_id_mul_two]
        simp only [Nat.add_sub_cancel]
        ring
      have hT : n * (n + 1) / 2 * 2 = n * (n + 1) :=
        Nat.div_mul_cancel (Nat.even_mul_succ_self n).two_dvd
      have hexp : 2 * (n * (n + 1) / 2) + 2 * (∑ m ∈ Finset.Ioc (n / 2) n, m) +
          2 * (∑ j ∈ Finset.Ico 2 n, (j + 1)) ≤ 3 * n * n := by
        have arith : ∀ e r A B T : ℕ, r ≤ 1 → 3 ≤ e →
            A * 2 = 2 * (e + 1 + r + 1) * (e + 2 + 1) + (e + 1 + r + 1) * (e + 1 + r) →
            B * 2 = 6 * (2 * e + 1 + r + 1) + (2 * e + 1 + r + 1) * (2 * e + 1 + r) →
            T * 2 = (2 * e + 4 + r) * (2 * e + 4 + r + 1) →
            2 * T + 2 * A + 2 * B ≤ 3 * (2 * e + 4 + r) * (2 * e + 4 + r) := by
          intro e r A B T hr he hA hB hT
          have hsq : 3 * e ≤ e * e := Nat.mul_le_mul_right e he
          rcases (show r = 0 ∨ r = 1 by omega) with rfl | rfl
          · ring_nf at hA hB hT hsq ⊢
            omega
          · ring_nf at hA hB hT hsq ⊢
            omega
        obtain ⟨e, he⟩ : ∃ e, n / 2 = e + 2 := ⟨n / 2 - 2, by omega⟩
        obtain ⟨r, hr1, hr⟩ : ∃ r, r ≤ 1 ∧ n = 2 * e + 4 + r := ⟨n - (2 * e + 4), by omega, by omega⟩
        have hc' : c = e + 1 + r := by omega
        have hd' : d = 2 * e + 1 + r := by omega
        rw [he, hc'] at hS1
        rw [hd'] at hS2
        have hT' : n * (n + 1) / 2 * 2 = (2 * e + 4 + r) * (2 * e + 4 + r + 1) := by rw [hT, hr]
        have := arith e r _ _ _ hr1 (by omega) hS1 hS2 hT'
        rw [he]
        rw [hr] at this ⊢
        exact this
      calc (2 ^ (n * (n + 1) / 2) * ((∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) *
              ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3))) ^ 2
          ≤ (2 ^ (n * (n + 1) / 2) * (2 ^ (∑ m ∈ Finset.Ioc (n / 2) n, m) *
              2 ^ (∑ j ∈ Finset.Ico 2 n, (j + 1)))) ^ 2 := by gcongr
        _ = 2 ^ (2 * (n * (n + 1) / 2) + 2 * (∑ m ∈ Finset.Ioc (n / 2) n, m) +
              2 * (∑ j ∈ Finset.Ico 2 n, (j + 1))) := by
          rw [← pow_add, ← pow_add, ← pow_mul]; congr 1; ring
        _ ≤ 2 ^ (3 * n * n) := Nat.pow_le_pow_right (by norm_num) hexp
  exact_mod_cast key
