import Mathlib
import Nodes.«spec-1a5ab7c3».Context

/-- erdos-1050, hole hden (erdos-1050--h1-v2--h3), ingredient 2, odd half, of annex 4670684d2f0d
on that node. Every denominator 2^(k - j) - 1 with 1 ≤ k - j ≤ n divides
M_n = ∏_{n/2 < m ≤ n} (2^m - 1), because m has the multiple m * (n / m) in (n/2, n]. Hence M_n
clears the inner sum p_k(n) = ∑_{j ≤ k} Qc n j / (2^(k - j) - 1) of `Aq` in h3 for any integer
coefficients (Qc n j is one by ingredient 1, spec-440db0f9). The j = k term divides by 2^0 - 1 = 0
and is 0 in ℚ, as in h3. The 2-adic half of ingredient 2 (v2(p_k(n)) ≥ k(k-1)/2) is not claimed. -/
theorem erdos_1050_upper_half_mersenne_clears (n k : ℕ) (hk : k ≤ n) (c : ℕ → ℤ) :
    ∃ z : ℤ, (z : ℚ) = (∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ m - 1)) *
      ∑ j ∈ Finset.range (k + 1), (c j : ℚ) / ((2 : ℚ) ^ (k - j) - 1) := by
  have hint : ∀ j ∈ Finset.range (k + 1), ∃ z : ℤ,
      (z : ℚ) = (∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ m - 1)) *
        ((c j : ℚ) / ((2 : ℚ) ^ (k - j) - 1)) := by
    intro j hj
    have hjk : j ≤ k := Nat.lt_succ_iff.mp (Finset.mem_range.mp hj)
    by_cases hjeq : j = k
    · subst hjeq
      exact ⟨0, by simp⟩
    · obtain ⟨d, hd⟩ : ∃ d, k - j = d + 1 := ⟨k - j - 1, by omega⟩
      rw [hd]
      have hdn : d + 1 ≤ n := by omega
      have ht : 1 ≤ n / (d + 1) := (Nat.one_le_div_iff (by omega)).mpr hdn
      have hP1 : (d + 1) * (n / (d + 1)) ≤ n := Nat.mul_div_le n (d + 1)
      have hP2 : n < (d + 1) * (n / (d + 1)) + (d + 1) := by
        have := Nat.lt_mul_div_succ n (show 0 < d + 1 by omega)
        rw [Nat.mul_succ] at this
        exact this
      have hP3 : (d + 1) ≤ (d + 1) * (n / (d + 1)) := Nat.le_mul_of_pos_right _ ht
      have hmem : (d + 1) * (n / (d + 1)) ∈ Finset.Ioc (n / 2) n := by
        rw [Finset.mem_Ioc]
        generalize (d + 1) * (n / (d + 1)) = P at hP1 hP2 hP3 ⊢
        omega
      have hdvd : ((2 : ℤ) ^ (d + 1) - 1) ∣ ∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℤ) ^ m - 1) := by
        refine dvd_trans ?_ (Finset.dvd_prod_of_mem _ hmem)
        have := sub_dvd_pow_sub_pow ((2 : ℤ) ^ (d + 1)) 1 (n / (d + 1))
        rw [one_pow, ← pow_mul] at this
        exact this
      obtain ⟨q, hq⟩ := hdvd
      have hne : ((2 : ℚ) ^ (d + 1) - 1) ≠ 0 := by
        have : (1 : ℚ) < 2 ^ (d + 1) := one_lt_pow₀ (by norm_num) (by omega)
        linarith
      refine ⟨c j * q, ?_⟩
      have hcast : (∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ m - 1)) =
          (((2 : ℤ) ^ (d + 1) - 1 : ℤ) : ℚ) * (q : ℚ) := by
        rw [← Int.cast_mul, ← hq]
        push_cast
        rfl
      rw [hcast]
      push_cast
      field_simp
  choose! g hg using hint
  refine ⟨∑ j ∈ Finset.range (k + 1), g j, ?_⟩
  push_cast
  rw [Finset.mul_sum]
  exact Finset.sum_congr rfl hg
