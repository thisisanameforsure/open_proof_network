import Mathlib

open scoped ArithmeticFunction.omega

theorem Opn.erdos_69_rational_dilated_tail_integral :
    ∀ (q : ℕ) (z : ℤ), (q : ℝ) * ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = z →
      ∀ a m : ℕ, a ≠ 0 → ∃ t : ℤ,
        (q : ℝ) * (∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
          + ∑ p ∈ a.primeFactors,
              ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)) = t := by
  intro q z hz a m ha
  have hdil : ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
      = ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ)
        - ∑ p ∈ a.primeFactors,
            ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) := by
    -- ω is the number of prime factors
    have hω : ∀ x : ℕ, ω x = x.primeFactors.card := fun x => by
      rw [ArithmeticFunction.cardDistinctFactors_apply]; rfl
    -- the pointwise identity ω(a n) + #{p ∣ a : p ∣ n} = ω a + ω n
    have hpt : ∀ n : ℕ, n ≠ 0 →
        (ω (a * n) : ℝ) = (ω n : ℝ) + (ω a : ℝ)
          - ∑ p ∈ a.primeFactors, (if p ∣ n then (1 : ℝ) else 0) := by
      intro n hn
      have hu : (a * n).primeFactors = a.primeFactors ∪ n.primeFactors := Nat.primeFactors_mul ha hn
      have hi : a.primeFactors ∩ n.primeFactors = a.primeFactors.filter (· ∣ n) := by
        ext p
        simp only [Finset.mem_inter, Finset.mem_filter, Nat.mem_primeFactors]
        constructor
        · rintro ⟨h1, h2⟩; exact ⟨h1, h2.2.1⟩
        · rintro ⟨h1, h2⟩; exact ⟨h1, h1.1, h2, hn⟩
      have hc := Finset.card_union_add_card_inter a.primeFactors n.primeFactors
      rw [← hu, hi] at hc
      have hs : ∑ p ∈ a.primeFactors, (if p ∣ n then (1 : ℝ) else 0)
          = ((a.primeFactors.filter (· ∣ n)).card : ℝ) := by
        rw [Finset.sum_ite, Finset.sum_const_zero, add_zero, Finset.sum_const, nsmul_eq_mul, mul_one]
      rw [hs, hω, hω, hω]
      have hc' : ((a * n).primeFactors.card : ℝ) + ((a.primeFactors.filter (· ∣ n)).card : ℝ)
          = (a.primeFactors.card : ℝ) + (n.primeFactors.card : ℝ) := by exact_mod_cast hc
      linarith
    -- summability tools
    have hgeo : ∀ c : ℝ, Summable (fun k : ℕ => ((k : ℝ) + c) * (1 / 2 : ℝ) ^ k) := by
      intro c
      have h1 := summable_pow_mul_geometric_of_norm_lt_one 1 (by norm_num [Real.norm_eq_abs] : ‖(1 / 2 : ℝ)‖ < 1)
      have h2 := (summable_geometric_of_lt_one (by norm_num : (0 : ℝ) ≤ 1 / 2) (by norm_num)).mul_left c
      refine (h1.add h2).congr (fun k => ?_)
      simp only [pow_one]; ring
    have hw : ∀ k : ℕ, (1 : ℝ) / 2 ^ (k + 1) ≤ (1 / 2 : ℝ) ^ k := by
      intro k
      rw [one_div_pow, pow_succ]
      apply one_div_le_one_div_of_le (by positivity)
      linarith [pow_pos (by norm_num : (0 : ℝ) < 2) k]
    have hωle : ∀ x : ℕ, (ω x : ℝ) ≤ x + 1 := by
      intro x
      have h1 : ω x ≤ x + 1 := by
        rw [hω]
        calc x.primeFactors.card ≤ (Finset.range (x + 1)).card :=
              Finset.card_le_card (fun p hp =>
                Finset.mem_range.2 (Nat.lt_succ_of_le (Nat.le_of_mem_primeFactors hp)))
          _ = x + 1 := Finset.card_range _
      exact_mod_cast h1
    have hS1 : Summable (fun k : ℕ => (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1)) := by
      refine Summable.of_nonneg_of_le (fun k => by positivity) (fun k => ?_) (hgeo ((m : ℝ) + 2))
      have h1 := hωle (m + (k + 1))
      have h2 := hw k
      have h3 : (0 : ℝ) ≤ (ω (m + (k + 1)) : ℝ) := by positivity
      calc (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) = (ω (m + (k + 1)) : ℝ) * (1 / 2 ^ (k + 1)) := by ring
        _ ≤ ((k : ℝ) + ((m : ℝ) + 2)) * (1 / 2 : ℝ) ^ k := by
          apply mul_le_mul _ h2 (by positivity) (by positivity)
          push_cast at h1; linarith
    have hS2 : Summable (fun k : ℕ => (1 : ℝ) / 2 ^ (k + 1)) := by
      refine Summable.of_nonneg_of_le (fun k => by positivity) hw ?_
      exact summable_geometric_of_lt_one (by norm_num) (by norm_num)
    have hS3 : ∀ p : ℕ, Summable (fun k : ℕ => (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)) := by
      intro p
      refine Summable.of_nonneg_of_le (fun k => by split_ifs <;> positivity) (fun k => ?_) hS2
      split_ifs <;> simp
    have hsum1 : ∑' k : ℕ, (1 : ℝ) / 2 ^ (k + 1) = 1 := by
      have : (fun k : ℕ => (1 : ℝ) / 2 ^ (k + 1)) = fun k => (1 / 2) * (1 / 2 : ℝ) ^ k := by
        funext k; rw [pow_succ, one_div_pow]; field_simp
      rw [this, tsum_mul_left, tsum_geometric_two]; norm_num
    -- assemble
    have hterm : ∀ k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
        = (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ) * (1 / 2 ^ (k + 1))
          - ∑ p ∈ a.primeFactors, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) := by
      intro k
      rw [hpt (m + (k + 1)) (by omega), ← Finset.sum_div]
      ring
    rw [tsum_congr hterm, Summable.tsum_sub (hS1.add (hS2.mul_left _)) (summable_sum (fun p _ => hS3 p)),
      Summable.tsum_add hS1 (hS2.mul_left _), tsum_mul_left, hsum1, mul_one,
      Summable.tsum_finsetSum (fun p _ => hS3 p)]
  -- integrality of q times the plain tail
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
  have hsum : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n) := by
    refine Summable.of_nonneg_of_le (fun n => by positivity) hbound ?_
    exact (summable_pow_mul_geometric_of_norm_lt_one 1 (by norm_num [Real.norm_eq_abs])).add
      (summable_geometric_of_lt_one (by norm_num) (by norm_num))
  have htail : ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1)
      = 2 ^ m * (∑' n : ℕ, (ω n : ℝ) / 2 ^ n
          - ∑ n ∈ Finset.range (m + 1), (ω n : ℝ) / 2 ^ n) := by
    have h := hsum.sum_add_tsum_nat_add (m + 1)
    have h2 : ∑' i : ℕ, (ω (i + (m + 1)) : ℝ) / 2 ^ (i + (m + 1))
        = (∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1)) / 2 ^ m := by
      rw [← tsum_div_const]
      refine tsum_congr (fun k => ?_)
      rw [show k + (m + 1) = m + (k + 1) by ring, show m + (k + 1) = (k + 1) + m by ring,
        pow_add, div_div]
    rw [h2] at h
    have h3 := eq_sub_of_add_eq' h
    rw [← h3]
    field_simp
  have hA : ∑ n ∈ Finset.range (m + 1), (q : ℝ) * (ω n : ℝ) * 2 ^ (m - n)
      = 2 ^ m * ((q : ℝ) * ∑ n ∈ Finset.range (m + 1), (ω n : ℝ) / 2 ^ n) := by
    rw [Finset.mul_sum, Finset.mul_sum]
    refine Finset.sum_congr rfl (fun n hn => ?_)
    have hn' : n ≤ m := Nat.lt_succ_iff.1 (Finset.mem_range.1 hn)
    rw [pow_sub₀ (2 : ℝ) two_ne_zero hn']
    field_simp
  refine ⟨2 ^ m * z - ∑ n ∈ Finset.range (m + 1), (q : ℤ) * ω n * 2 ^ (m - n) + q * ω a, ?_⟩
  push_cast
  rw [hdil, sub_add_cancel, htail]
  linear_combination (2 : ℝ) ^ m * hz + hA
