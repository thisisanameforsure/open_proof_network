import Mathlib

open scoped ArithmeticFunction.omega

/-- If the series equals a/b, then b times every rescaled tail
T_N = ∑_{j ≥ 0} ω(N+1+j) / 2^(j+1) is an integer (any denominator b, not only 2^m). -/
theorem tail_integral (b : ℕ) (hb : 0 < b) (a : ℤ)
    (hx : ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = (a : ℝ) / b) :
    ∀ N : ℕ, ∃ z : ℤ,
      (b : ℝ) * ∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1) = (z : ℝ) := by
  intro N
  have hsum : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n) := by
    have hbound : ∀ n : ℕ,
        (ω n : ℝ) / 2 ^ n ≤ (n : ℝ) ^ 1 * (1 / 2 : ℝ) ^ n + (1 / 2 : ℝ) ^ n := by
      intro n
      have h1 : ω n ≤ n + 1 := by
        rw [ArithmeticFunction.cardDistinctFactors_apply]
        calc n.primeFactorsList.dedup.length = n.primeFactors.card := rfl
          _ ≤ (Finset.range (n + 1)).card :=
              Finset.card_le_card (fun p hp =>
                Finset.mem_range.2 (Nat.lt_succ_of_le (Nat.le_of_mem_primeFactors hp)))
          _ = n + 1 := Finset.card_range _
      have h2 : (ω n : ℝ) ≤ (n : ℝ) + 1 := by exact_mod_cast h1
      have h4 : (0 : ℝ) ≤ ((2 : ℝ) ^ n)⁻¹ := by positivity
      rw [pow_one, one_div, inv_pow, div_eq_mul_inv]
      nlinarith [mul_le_mul_of_nonneg_right h2 h4]
    refine Summable.of_nonneg_of_le (fun n => by positivity) hbound ?_
    exact (summable_pow_mul_geometric_of_norm_lt_one 1 (by norm_num [Real.norm_eq_abs])).add
      (summable_geometric_of_lt_one (by norm_num) (by norm_num))
  have h := hsum.sum_add_tsum_nat_add (N + 1)
  have htail : ∑' j : ℕ, (ω (j + (N + 1)) : ℝ) / 2 ^ (j + (N + 1))
      = (∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1)) / 2 ^ N := by
    rw [← tsum_div_const]
    congr 1
    funext j
    rw [show j + (N + 1) = N + 1 + j by ring, show N + 1 + j = (j + 1) + N by ring, pow_add]
    rw [show (j + 1) + N = N + 1 + j by ring]
    field_simp
  have hbR : (b : ℝ) ≠ 0 := by exact_mod_cast hb.ne'
  refine ⟨a * 2 ^ N - (b : ℤ) * ∑ i ∈ Finset.range (N + 1), (ω i : ℤ) * 2 ^ (N - i), ?_⟩
  have hpow : ∀ i : ℕ, i ≤ N → (2 : ℝ) ^ (N - i) = 2 ^ N / 2 ^ i := fun i hi =>
    pow_sub₀ 2 (by norm_num) hi
  have hT : ∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1)
      = 2 ^ N * ((a : ℝ) / b - ∑ i ∈ Finset.range (N + 1), (ω i : ℝ) / 2 ^ i) := by
    rw [← hx, ← h, htail]
    field_simp
    ring
  have hs : ∑ i ∈ Finset.range (N + 1), (b : ℝ) * ((ω i : ℝ) * 2 ^ (N - i))
      = ∑ i ∈ Finset.range (N + 1), (b : ℝ) * (2 ^ N * ((ω i : ℝ) / 2 ^ i)) := by
    refine Finset.sum_congr rfl (fun i hi => ?_)
    rw [hpow i (Nat.lt_succ_iff.mp (Finset.mem_range.mp hi))]
    ring
  rw [hT]
  push_cast
  rw [Finset.mul_sum, hs, ← Finset.mul_sum, ← Finset.mul_sum]
  field_simp
