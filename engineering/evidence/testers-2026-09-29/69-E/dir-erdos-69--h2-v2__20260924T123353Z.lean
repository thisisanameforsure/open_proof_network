import Mathlib

open scoped ArithmeticFunction.omega
open Filter Topology

theorem chk_anc :
    Irrational <| ∑' n, ω (n + 2) / 2 ^ (n + 2) := by
  sorry

theorem chk_hole : (∑' n : ℕ, (ω n : ℝ) / 2 ^ n
      = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) →
    Irrational (∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) := by
  sorry



theorem circular_h2_v2 :
    (Irrational <| ∑' n, ω (n + 2) / 2 ^ (n + 2)) →
    ((∑' n : ℕ, (ω n : ℝ) / 2 ^ n
      = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) →
    Irrational (∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1))) := by
  intro hroot hL
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
  have root_series_eq :
      ∑' n : ℕ, (ω (n + 2) : ℝ) / 2 ^ (n + 2) = ∑' n : ℕ, (ω n : ℝ) / 2 ^ n := by
    have h := hsum.sum_add_tsum_nat_add 2
    rw [← h]
    simp [Finset.sum_range_succ]
  rw [← hL, ← root_series_eq]
  exact hroot

example : (type_of% @chk_anc → type_of% @chk_hole) = type_of% @circular_h2_v2 := rfl
