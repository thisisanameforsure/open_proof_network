import Mathlib

theorem Opn.erdos_69_summable_prime_reciprocal :
    Summable (fun p : Nat.Primes => (1 : ℝ) / (2 ^ (p : ℕ) - 1)) := by
  have hg : Summable (fun n : ℕ => (2 : ℝ) * (1 / 2) ^ n) :=
    summable_geometric_two.mul_left 2
  have hsub : Summable (fun p : Nat.Primes => (2 : ℝ) * (1 / 2) ^ (p : ℕ)) :=
    hg.comp_injective Subtype.val_injective
  refine Summable.of_nonneg_of_le (fun p => ?_) (fun p => ?_) hsub
  · have h1 : (1 : ℝ) ≤ 2 ^ (p : ℕ) := one_le_pow₀ (by norm_num)
    have h0 : (0 : ℝ) ≤ 2 ^ (p : ℕ) - 1 := by linarith
    positivity
  · have hp : 1 ≤ (p : ℕ) := p.2.one_lt.le
    have h2 : (2 : ℝ) ^ (p : ℕ) = 2 * 2 ^ ((p : ℕ) - 1) := by
      rw [← pow_succ']
      congr 1
      omega
    have hpos : (0 : ℝ) < 2 ^ ((p : ℕ) - 1) := by positivity
    have hden : (2 : ℝ) ^ ((p : ℕ) - 1) ≤ 2 ^ (p : ℕ) - 1 := by
      have h1 : (1 : ℝ) ≤ 2 ^ ((p : ℕ) - 1) := one_le_pow₀ (by norm_num)
      rw [h2]
      linarith
    calc (1 : ℝ) / (2 ^ (p : ℕ) - 1) ≤ 1 / 2 ^ ((p : ℕ) - 1) :=
          one_div_le_one_div_of_le hpos hden
      _ = 2 * (1 / 2) ^ (p : ℕ) := by
          rw [one_div_pow, h2]
          field_simp
