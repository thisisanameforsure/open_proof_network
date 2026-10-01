import Mathlib

theorem residue_test : ∀ n : ℕ, 1 ≤ n → (∑' j : ℕ, (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹)) = (∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k)))) * (∑' j : ℕ, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (j + 1))⁻¹) - ((∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (∑ i ∈ Finset.Icc 1 k, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ i)⁻¹)) - ∑ i ∈ Finset.Icc 1 (n - 1), (∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (((8 / 3 : ℝ) * (2 : ℝ) ^ k) ^ i)⁻¹) / ((2 : ℝ) ^ i - 1)) := by
  intro n hn
  -- The one hole: the partial-fraction identity at x = 2^m (pure algebra, no series).
  have pf : ∀ m : ℕ, 1 ≤ m → (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((m : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (m : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (m : ℕ)))⁻¹) = ((∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (k + m))⁻¹) + ∑ i ∈ Finset.Icc 1 (n - 1), (∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (((8 / 3 : ℝ) * (2 : ℝ) ^ k) ^ i)⁻¹) * (((2 : ℝ) ^ m) ^ i)⁻¹) := sorry
  -- Summability of the two families of pieces.
  have hT : ∀ k : ℕ, Summable (fun m : ℕ => (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (k + (m + 1)))⁻¹) := by
    intro k
    refine Summable.of_norm_bounded (summable_geometric_of_lt_one (by norm_num : (0 : ℝ) ≤ 1 / 2) (by norm_num)) (fun m => ?_)
    have h1 : (1 : ℝ) ≤ 2 ^ k := one_le_pow₀ (by norm_num)
    have h2 : (1 : ℝ) ≤ 2 ^ m := one_le_pow₀ (by norm_num)
    have he : (2 : ℝ) ^ (k + (m + 1)) = 2 * 2 ^ k * 2 ^ m := by ring
    have hneg : (1 : ℝ) - 8 / 3 * 2 ^ (k + (m + 1)) < 0 := by rw [he]; nlinarith
    rw [Real.norm_eq_abs, abs_inv, abs_of_neg hneg, one_div_pow, one_div]
    exact inv_anti₀ (by positivity) (by rw [he]; nlinarith)
  have hGeo : ∀ i : ℕ, 1 ≤ i → ∑' m : ℕ, (((2 : ℝ) ^ (m + 1)) ^ i)⁻¹ = ((2 : ℝ) ^ i - 1)⁻¹ := by
    intro i hi
    have h2 : (2 : ℝ) ≤ 2 ^ i := by
      calc (2 : ℝ) = 2 ^ 1 := (pow_one 2).symm
        _ ≤ 2 ^ i := pow_le_pow_right₀ (by norm_num) hi
    have hr0 : (0 : ℝ) ≤ ((2 : ℝ) ^ i)⁻¹ := by positivity
    have hr1 : ((2 : ℝ) ^ i)⁻¹ < 1 := inv_lt_one_of_one_lt₀ (by linarith)
    have hc : ∀ m : ℕ, (((2 : ℝ) ^ (m + 1)) ^ i)⁻¹ = ((2 : ℝ) ^ i)⁻¹ * (((2 : ℝ) ^ i)⁻¹) ^ m := by
      intro m
      rw [← pow_succ', inv_pow, ← pow_mul, ← pow_mul, mul_comm]
    rw [tsum_congr hc, tsum_mul_left, tsum_geometric_of_lt_one hr0 hr1]
    have h3 : (2 : ℝ) ^ i - 1 ≠ 0 := by linarith
    have h4 : (2 : ℝ) ^ i ≠ 0 := by positivity
    field_simp
  have hGs : ∀ i : ℕ, 1 ≤ i → Summable (fun m : ℕ => (((2 : ℝ) ^ (m + 1)) ^ i)⁻¹) := by
    intro i hi
    by_contra hns
    have := tsum_eq_zero_of_not_summable hns
    rw [hGeo i hi] at this
    have h2 : (2 : ℝ) ≤ 2 ^ i := by
      calc (2 : ℝ) = 2 ^ 1 := (pow_one 2).symm
        _ ≤ 2 ^ i := pow_le_pow_right₀ (by norm_num) hi
    have : ((2 : ℝ) ^ i - 1)⁻¹ ≠ 0 := inv_ne_zero (by linarith)
    contradiction
  have hz0 : Summable (fun j : ℕ => (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (j + 1))⁻¹) := by
    simpa using hT 0
  have hIcc : ∀ k : ℕ, ∑ i ∈ Finset.range k, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (i + 1))⁻¹ = ∑ i ∈ Finset.Icc 1 k, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ i)⁻¹ := by
    intro k
    induction k with
    | zero => simp
    | succ k ih => rw [Finset.sum_range_succ, ih, Finset.sum_Icc_succ_top (by omega)]
  have hTail : ∀ k : ℕ, ∑' m : ℕ, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (k + (m + 1)))⁻¹ = (∑' j : ℕ, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (j + 1))⁻¹) - ∑ i ∈ Finset.Icc 1 k, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ i)⁻¹ := by
    intro k
    have hs := hz0.sum_add_tsum_nat_add k
    rw [hIcc k] at hs
    rw [← hs, add_sub_cancel_left]
    exact tsum_congr (fun m => by rw [show k + (m + 1) = m + k + 1 by omega])
  -- The series E(n) summed from m = 1: its first n - 1 terms vanish.
  have hRs1 : Summable (fun m : ℕ => ∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (k + (m + 1)))⁻¹) :=
    summable_sum (fun k _ => (hT k).mul_left _)
  have hRs2 : Summable (fun m : ℕ => ∑ i ∈ Finset.Icc 1 (n - 1), (∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (((8 / 3 : ℝ) * (2 : ℝ) ^ k) ^ i)⁻¹) * (((2 : ℝ) ^ (m + 1)) ^ i)⁻¹) :=
    summable_sum (fun i hi => (hGs i (Finset.mem_Icc.mp hi).1).mul_left _)
  have hRs : Summable (fun m : ℕ => ((∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (k + (m + 1)))⁻¹) + ∑ i ∈ Finset.Icc 1 (n - 1), (∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (((8 / 3 : ℝ) * (2 : ℝ) ^ k) ^ i)⁻¹) * (((2 : ℝ) ^ (m + 1)) ^ i)⁻¹)) := hRs1.add hRs2
  have hGsum : Summable (fun m : ℕ => (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((((m + 1) : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - ((m + 1) : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + ((m + 1) : ℕ)))⁻¹)) :=
    hRs.congr (fun m => (pf (m + 1) (by omega)).symm)
  have hshift := hGsum.sum_add_tsum_nat_add (n - 1)
  have hzero : ∑ i ∈ Finset.range (n - 1), (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((((i + 1) : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - ((i + 1) : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + ((i + 1) : ℕ)))⁻¹) = 0 := by
    refine Finset.sum_eq_zero (fun i hi => ?_)
    have hi' : i + 1 ∈ Finset.Icc 1 (n - 1) := by
      rw [Finset.mem_range] at hi
      rw [Finset.mem_Icc]; omega
    refine mul_eq_zero_of_right _ (Finset.prod_eq_zero hi' ?_)
    simp
  rw [hzero, zero_add] at hshift
  have hE : (∑' j : ℕ, (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹)) = ∑' m : ℕ, (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((((m + 1) : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - ((m + 1) : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + ((m + 1) : ℕ)))⁻¹) := by
    rw [← hshift]
    exact tsum_congr (fun j => by rw [show j + (n - 1) + 1 = n + j by omega])
  rw [hE, tsum_congr (fun m => pf (m + 1) (by omega)), hRs1.tsum_add hRs2,
    Summable.tsum_finsetSum (fun k _ => (hT k).mul_left _),
    Summable.tsum_finsetSum (fun i hi => (hGs i (Finset.mem_Icc.mp hi).1).mul_left _),
    Finset.sum_congr (s₁ := Finset.Icc 1 n) rfl (fun k _ => by rw [tsum_mul_left, hTail k]),
    Finset.sum_congr (s₁ := Finset.Icc 1 (n - 1)) rfl (fun i hi => by rw [tsum_mul_left, hGeo i (Finset.mem_Icc.mp hi).1])]
  simp only [mul_sub, Finset.sum_sub_distrib, Finset.sum_mul, div_eq_mul_inv]
  ring
