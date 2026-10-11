import Mathlib
import Nodes.«spec-10c6e2b9».Context

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3), ingredient 3 of annex 4670684d2f0d on that node:
the size bound for the candidate common denominator
D_n = 2^(n(n+1)/2) * ∏_{n/2 < m ≤ n} (2^m - 1) * ∏_{2 ≤ j < n} (2^(j+1) - 3),
namely D_n^2 ≤ 2^(3 n^2), for every n except 5 and 7 (where it fails: D_5^2 > 2^75 by 0.1 bit,
and for n = 5, 7 the annex gives the least common denominators instead). The odd factor
∏_{n/2 < m ≤ n} (2^m - 1) is the one spec-1a5ab7c3 shows clears the p_k(n). In ℕ every
subtraction here is exact: 2^m ≥ 1 and 2^(j+1) ≥ 8. -/
theorem erdos_1050_hden_size_bound (n : ℕ) (h5 : n ≠ 5) (h7 : n ≠ 7) :
    (2 ^ (n * (n + 1) / 2) * (∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) *
      ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3)) ^ 2 ≤ 2 ^ (3 * n * n) := by
  have key : ∀ n : ℕ, (2 ^ (n * (n + 1) / 2) * (if n = 5 then 409045 else if n = 7 then 1298717875 else
          (∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) * ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3) : ℕ)) ^ 2 ≤
      2 ^ (3 * n * n) := by
    intro n
    rcases (show n ≤ 9 ∨ 10 ≤ n by omega) with hn | hn
    · interval_cases n <;> decide
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
        have hh5 : 5 ≤ n / 2 := by omega
        have hsq : 5 * (n / 2) ≤ (n / 2) * (n / 2) := Nat.mul_le_mul_right _ hh5
        rcases (show n = 2 * (n / 2) ∨ n = 2 * (n / 2) + 1 by omega) with hr | hr
        · have hc' : c = n / 2 - 1 := by omega
          have hd' : d = 2 * (n / 2) - 3 := by omega
          nlinarith
        · have hc' : c = n / 2 := by omega
          have hd' : d = 2 * (n / 2) - 2 := by omega
          nlinarith
      calc (2 ^ (n * (n + 1) / 2) * ((∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1)) *
              ∏ j ∈ Finset.Ico 2 n, (2 ^ (j + 1) - 3))) ^ 2
          ≤ (2 ^ (n * (n + 1) / 2) * (2 ^ (∑ m ∈ Finset.Ioc (n / 2) n, m) *
              2 ^ (∑ j ∈ Finset.Ico 2 n, (j + 1)))) ^ 2 := by gcongr
        _ = 2 ^ (2 * (n * (n + 1) / 2) + 2 * (∑ m ∈ Finset.Ioc (n / 2) n, m) +
              2 * (∑ j ∈ Finset.Ico 2 n, (j + 1))) := by
          rw [← pow_add, ← pow_add, ← pow_mul]; congr 1; ring
        _ ≤ 2 ^ (3 * n * n) := Nat.pow_le_pow_right (by norm_num) hexp
  have := key n
  rw [if_neg h5, if_neg h7, ← mul_assoc] at this
  exact this
