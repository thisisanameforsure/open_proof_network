import Mathlib

open scoped ArithmeticFunction.omega

/-- (a) The root's series, as elaborated: a real series, the cast on `ω (n + 2)`, the power real. -/
example : (∑' n, ω (n + 2) / 2 ^ (n + 2) : ℝ)
    = ∑' n : ℕ, ((ω (n + 2) : ℕ) : ℝ) / (2 : ℝ) ^ (n + 2) := rfl

/-- (b) `ω` is `ArithmeticFunction.cardDistinctFactors`, the number of distinct prime divisors. -/
example (n : ℕ) : ω n = n.primeFactors.card := by
  rw [ArithmeticFunction.cardDistinctFactors_apply, ← List.card_toFinset]
  rfl

example : ω 12 = 2 := by
  rw [ArithmeticFunction.cardDistinctFactors_apply, show (12 : ℕ) = 2 ^ 2 * 3 by norm_num]
  norm_num [Nat.primeFactorsList]

/-- (c) The reindexing: the root's `∑' n, f (n + 2)` is the informal `∑_{m ≥ 2} ω(m)/2^m`. -/
example : (∑' n, ω (n + 2) / 2 ^ (n + 2) : ℝ)
    = ∑' m : {m : ℕ // 2 ≤ m}, (ω (m : ℕ) : ℝ) / 2 ^ (m : ℕ) := by
  let e : ℕ ≃ {m : ℕ // 2 ≤ m} :=
    { toFun := fun n => ⟨n + 2, by omega⟩
      invFun := fun m => (m : ℕ) - 2
      left_inv := fun n => by simp
      right_inv := fun m => by ext; simp; omega }
  exact e.tsum_eq (fun m : {m : ℕ // 2 ≤ m} => (ω (m : ℕ) : ℝ) / 2 ^ (m : ℕ))

/-- (d) The series is summable, so `tsum` is its true sum and not the junk value `0`. -/
example : Summable (fun n : ℕ => (ω (n + 2) : ℝ) / 2 ^ (n + 2)) := by
  have hsum : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n) := by
    refine Summable.of_nonneg_of_le (fun n => by positivity) (fun n => ?_)
      (summable_pow_mul_geometric_of_norm_lt_one (R := ℝ) 1 (r := 1 / 2) (by norm_num [Real.norm_eq_abs]))
    have h1 : ω n ≤ n := by
      rw [ArithmeticFunction.cardDistinctFactors_apply, ← List.card_toFinset]
      exact (Finset.card_le_card (fun p hp => Finset.mem_Icc.2
        ⟨(Nat.prime_of_mem_primeFactorsList (List.mem_toFinset.1 hp)).one_lt.le,
         Nat.le_of_mem_primeFactorsList (List.mem_toFinset.1 hp)⟩)).trans (by simp)
    have h2 : (ω n : ℝ) ≤ n := by exact_mod_cast h1
    rw [pow_one, div_eq_mul_inv, one_div, inv_pow]
    exact mul_le_mul_of_nonneg_right h2 (by positivity)
  exact (summable_nat_add_iff 2).mpr hsum
