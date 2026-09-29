import Mathlib

open scoped ArithmeticFunction.omega

/-- ω of a dilation, pointwise: the primes of `a` that divide `n` are counted once. -/
theorem omega_mul_eq (a n : ℕ) (ha : a ≠ 0) (hn : n ≠ 0) :
    (ω (a * n) : ℝ) = (ω n : ℝ) + (ω a : ℝ)
      - ∑ p ∈ a.primeFactors, (if p ∣ n then (1 : ℝ) else 0) := by
  have hω : ∀ m : ℕ, ω m = m.primeFactors.card := fun m => by
    rw [ArithmeticFunction.cardDistinctFactors_apply]; rfl
  have hunion : (a * n).primeFactors.card + (a.primeFactors ∩ n.primeFactors).card
      = a.primeFactors.card + n.primeFactors.card := by
    rw [Nat.primeFactors_mul ha hn, Finset.card_union_add_card_inter]
  have hinter : a.primeFactors ∩ n.primeFactors = a.primeFactors.filter (· ∣ n) := by
    ext p
    simp only [Finset.mem_inter, Finset.mem_filter, Nat.mem_primeFactors]
    constructor
    · rintro ⟨h1, h2⟩; exact ⟨h1, h2.2.1⟩
    · rintro ⟨h1, h2⟩; exact ⟨h1, h1.1, h2, hn⟩
  have hsum : (∑ p ∈ a.primeFactors, (if p ∣ n then (1 : ℝ) else 0))
      = ((a.primeFactors.filter (· ∣ n)).card : ℝ) := by
    rw [Finset.card_filter]; push_cast; rfl
  rw [hsum, ← hinter, hω, hω, hω]
  have : ((a * n).primeFactors.card : ℝ) + ((a.primeFactors ∩ n.primeFactors).card : ℝ)
      = (a.primeFactors.card : ℝ) + (n.primeFactors.card : ℝ) := by exact_mod_cast hunion
  linarith

/-- The dilated tail: T_m plus ω a, minus the mass of the primes of `a` dividing the
shifted integers. The cofactor's prime count cancels, and what is left is a
divisibility pattern, which the Chinese remainder theorem controls exactly. -/
theorem dilated_tail (a m : ℕ) (ha : a ≠ 0) :
    ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
      = ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ)
        - ∑ p ∈ a.primeFactors,
            ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) := by
  have hsum0 : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n) := by
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
  have hsA : Summable (fun k : ℕ => (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1)) := by
    have h := ((summable_nat_add_iff (m + 1)).mpr hsum0).mul_left ((2 : ℝ) ^ m)
    refine h.congr (fun k => ?_)
    rw [show k + (m + 1) = m + (k + 1) by ring, show m + (k + 1) = (k + 1) + m by ring,
      pow_add]
    field_simp
  have hgeo : Summable (fun k : ℕ => (1 : ℝ) / 2 ^ (k + 1)) := by
    refine (summable_geometric_two.mul_left (1 / 2 : ℝ)).congr (fun k => ?_)
    rw [one_div, one_div, ← inv_pow, pow_succ, mul_comm]
  have h1 : ∑' k : ℕ, (1 : ℝ) / 2 ^ (k + 1) = 1 := by
    calc ∑' k : ℕ, (1 : ℝ) / 2 ^ (k + 1) = ∑' n : ℕ, (1 : ℝ) / 2 / 2 ^ n :=
          tsum_congr (fun k => by ring)
      _ = 1 := tsum_geometric_two' 1
  have hsI : ∀ p ∈ a.primeFactors,
      Summable (fun k : ℕ => (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)) := by
    intro p _
    refine Summable.of_nonneg_of_le (fun k => ?_) (fun k => ?_) hgeo
    · split_ifs <;> positivity
    · split_ifs
      · exact le_rfl
      · rw [zero_div]; positivity
  have hpt : ∀ k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
      = ((ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ) * (1 / 2 ^ (k + 1)))
        - ∑ p ∈ a.primeFactors, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) := by
    intro k
    rw [omega_mul_eq a _ ha (by omega), ← Finset.sum_div]
    ring
  rw [tsum_congr hpt, (hsA.add (hgeo.mul_left _)).tsum_sub (summable_sum hsI),
    hsA.tsum_add (hgeo.mul_left _), tsum_mul_left, h1, Summable.tsum_finsetSum hsI, mul_one]
