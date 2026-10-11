import Mathlib

theorem den_test : ∃ b : ℕ → ℤ, ∀ n : ℕ, 1 ≤ n → (b n : ℝ) = (9 : ℝ) ^ n * ((Nat.factorial (n - 2) : ℝ) * (∏ k ∈ Finset.Icc 1 n, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ k)) * (∏ k ∈ Finset.Icc ((n + 1) / 2) n, (1 - (2 : ℝ) ^ k))) * (∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k)))) := by
  have key : ∀ n : ℕ, 1 ≤ n → ∃ z : ℤ, (z : ℝ) = (3 : ℝ) ^ (n - 1) * (∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k)))) := by
    intro n hn
    have hr0 : ∀ k : ℕ, ((8 : ℝ) * 2 ^ k) ≠ 0 := fun k => by positivity
    have hvinj : Set.InjOn (fun k : ℕ => ((8 : ℝ) * 2 ^ k)⁻¹) (Finset.Icc 1 n : Set ℕ) := by
      intro a _ b _ hab
      have h : (2 : ℝ) ^ a = 2 ^ b := by
        have := inv_injective hab
        exact mul_left_cancel₀ (by norm_num : (8 : ℝ) ≠ 0) this
      exact pow_right_injective₀ (by norm_num : (0 : ℝ) < 2) (by norm_num) h
    -- (1) the polynomial partial-fraction identity, by agreement at the n nodes 1/r_k
    have hid : (-∏ t ∈ Finset.Icc 1 (n - 1), (Polynomial.C (3 : ℝ) * Polynomial.X - Polynomial.C ((2 : ℝ) ^ t))) = ∑ k ∈ Finset.Icc 1 n, Polynomial.C ((-∏ t ∈ Finset.Icc 1 (n - 1), (Polynomial.C (3 : ℝ) * Polynomial.X - Polynomial.C ((2 : ℝ) ^ t))).eval ((8 : ℝ) * 2 ^ k)⁻¹ * (∏ j ∈ (Finset.Icc 1 n).erase k, (1 - ((8 : ℝ) * 2 ^ j) / ((8 : ℝ) * 2 ^ k)))⁻¹) * (∏ j ∈ (Finset.Icc 1 n).erase k, (1 - Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X)) := by
      refine Polynomial.eq_of_natDegree_lt_card_of_eval_eq' _ _ ((Finset.Icc 1 n).image (fun k : ℕ => ((8 : ℝ) * 2 ^ k)⁻¹)) ?_ ?_
      · intro y hy
        obtain ⟨k, hk, rfl⟩ := Finset.mem_image.mp hy
        rw [Polynomial.eval_finsetSum, Finset.sum_eq_single_of_mem k hk]
        · rw [Polynomial.eval_mul, Polynomial.eval_C, Polynomial.eval_prod]
          simp only [Polynomial.eval_sub, Polynomial.eval_one, Polynomial.eval_mul, Polynomial.eval_C, Polynomial.eval_X]
          have hne : ∏ j ∈ (Finset.Icc 1 n).erase k, (1 - ((8 : ℝ) * 2 ^ j) / ((8 : ℝ) * 2 ^ k)) ≠ 0 := by
            refine Finset.prod_ne_zero_iff.mpr (fun j hj => ?_)
            have hjk : j ≠ k := Finset.ne_of_mem_erase hj
            intro h0
            have : ((8 : ℝ) * 2 ^ j) = ((8 : ℝ) * 2 ^ k) := by
              have := hr0 k
              field_simp at h0
              linarith
            exact hjk (pow_right_injective₀ (by norm_num : (0 : ℝ) < 2) (by norm_num) (mul_left_cancel₀ (by norm_num : (8 : ℝ) ≠ 0) this))
          rw [mul_assoc, ← Finset.prod_congr rfl (fun j _ => by rw [div_eq_mul_inv, mul_comm (((8 : ℝ) * 2 ^ j)) _] : ∀ j ∈ (Finset.Icc 1 n).erase k, (1 - ((8 : ℝ) * 2 ^ j) / ((8 : ℝ) * 2 ^ k)) = 1 - ((8 : ℝ) * 2 ^ j) * ((8 : ℝ) * 2 ^ k)⁻¹), inv_mul_cancel₀ hne, mul_one]
        · intro i hi hik
          rw [Polynomial.eval_mul, Polynomial.eval_prod]
          refine mul_eq_zero_of_right _ (Finset.prod_eq_zero (i := k) (Finset.mem_erase.mpr ⟨Ne.symm hik, hk⟩) ?_)
          simp only [Polynomial.eval_sub, Polynomial.eval_one, Polynomial.eval_mul, Polynomial.eval_C, Polynomial.eval_X]
          rw [mul_inv_cancel₀ (hr0 k), sub_self]
      · rw [Finset.card_image_of_injOn hvinj, Nat.card_Icc]
        have hQdeg : (-∏ t ∈ Finset.Icc 1 (n - 1), (Polynomial.C (3 : ℝ) * Polynomial.X - Polynomial.C ((2 : ℝ) ^ t))).natDegree ≤ n - 1 := by
          rw [Polynomial.natDegree_neg]
          refine (Polynomial.natDegree_prod_le _ _).trans ?_
          refine (Finset.sum_le_sum (g := fun _ => 1) (fun t _ => ?_)).trans (le_of_eq ?_)
          · compute_degree
          · simp only [Finset.sum_const, smul_eq_mul, mul_one, Nat.card_Icc]; omega
        have hRdeg : (∑ k ∈ Finset.Icc 1 n, Polynomial.C ((-∏ t ∈ Finset.Icc 1 (n - 1), (Polynomial.C (3 : ℝ) * Polynomial.X - Polynomial.C ((2 : ℝ) ^ t))).eval ((8 : ℝ) * 2 ^ k)⁻¹ * (∏ j ∈ (Finset.Icc 1 n).erase k, (1 - ((8 : ℝ) * 2 ^ j) / ((8 : ℝ) * 2 ^ k)))⁻¹) * (∏ j ∈ (Finset.Icc 1 n).erase k, (1 - Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X))).natDegree ≤ n - 1 := by
          refine Polynomial.natDegree_sum_le_of_forall_le _ _ (fun k hk => ?_)
          refine (Polynomial.natDegree_C_mul_le _ _).trans ((Polynomial.natDegree_prod_le _ _).trans ?_)
          refine (Finset.sum_le_sum (g := fun _ => 1) (fun j _ => ?_)).trans (le_of_eq ?_)
          · compute_degree
          · simp only [Finset.sum_const, smul_eq_mul, mul_one]
            rw [Finset.card_erase_of_mem hk, Nat.card_Icc]; omega
        omega
    -- (2) coefficient n - 1 of T_k * P is r_k ^ (n - 1)
    have hU : ∀ (S : Finset ℕ), ∀ d < n, (∏ j ∈ S, (1 - (Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X) ^ n)).coeff d = if d = 0 then 1 else 0 := by
      intro S
      induction S using Finset.induction_on with
      | empty => intro d hd; simp [Polynomial.coeff_one]
      | insert a S ha ih =>
        intro d hd
        rw [Finset.prod_insert ha, sub_mul, one_mul, Polynomial.coeff_sub, mul_pow, ← Polynomial.C_pow, mul_assoc,
          Polynomial.coeff_C_mul, Polynomial.coeff_X_pow_mul', if_neg (by omega), mul_zero, sub_zero, ih d hd]
    have hG : ∀ k : ℕ, (∑ i ∈ Finset.range n, (Polynomial.C ((8 : ℝ) * 2 ^ k) * Polynomial.X) ^ i).coeff (n - 1) = ((8 : ℝ) * 2 ^ k) ^ (n - 1) := by
      intro k
      simp only [mul_pow, ← Polynomial.C_pow, Polynomial.finsetSum_coeff, Polynomial.coeff_C_mul_X_pow]
      rw [Finset.sum_ite_eq (Finset.range n) (n - 1), if_pos (Finset.mem_range.mpr (by omega))]
    have hTP : ∀ k ∈ Finset.Icc 1 n, ((∏ j ∈ (Finset.Icc 1 n).erase k, (1 - Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X)) * (∏ j ∈ Finset.Icc 1 n, (∑ i ∈ Finset.range n, (Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X) ^ i))).coeff (n - 1) = ((8 : ℝ) * 2 ^ k) ^ (n - 1) := by
      intro k hk
      have hsplitP : (∏ j ∈ Finset.Icc 1 n, (∑ i ∈ Finset.range n, (Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X) ^ i)) = (∑ i ∈ Finset.range n, (Polynomial.C ((8 : ℝ) * 2 ^ k) * Polynomial.X) ^ i) * ∏ j ∈ (Finset.Icc 1 n).erase k, (∑ i ∈ Finset.range n, (Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X) ^ i) :=
        (Finset.mul_prod_erase _ (fun j => (∑ i ∈ Finset.range n, (Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X) ^ i)) hk).symm
      have hprod : (∏ j ∈ (Finset.Icc 1 n).erase k, (1 - Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X)) * (∏ j ∈ Finset.Icc 1 n, (∑ i ∈ Finset.range n, (Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X) ^ i)) = (∑ i ∈ Finset.range n, (Polynomial.C ((8 : ℝ) * 2 ^ k) * Polynomial.X) ^ i) * ∏ j ∈ (Finset.Icc 1 n).erase k, (1 - (Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X) ^ n) := by
        rw [hsplitP, mul_left_comm, ← Finset.prod_mul_distrib]
        congr 1
        refine Finset.prod_congr rfl (fun j _ => ?_)
        rw [mul_neg_geom_sum]
      obtain ⟨E, hE⟩ : Polynomial.X ^ n ∣ (∏ j ∈ (Finset.Icc 1 n).erase k, (1 - (Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X) ^ n)) - 1 :=
        Polynomial.X_pow_dvd_iff.mpr (fun d hd => by
        rw [Polynomial.coeff_sub, hU _ d hd, Polynomial.coeff_one]; split_ifs <;> simp_all)
      rw [hprod, show ∏ j ∈ (Finset.Icc 1 n).erase k, (1 - (Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X) ^ n) = 1 + Polynomial.X ^ n * E by rw [← hE]; ring,
        mul_add, mul_one, Polynomial.coeff_add, mul_left_comm, Polynomial.coeff_X_pow_mul', if_neg (by omega), add_zero, hG]
    -- (3) so coefficient n - 1 of Qt * P is the sum of C_k r_k^(n-1)
    have hQP : ((-∏ t ∈ Finset.Icc 1 (n - 1), (Polynomial.C (3 : ℝ) * Polynomial.X - Polynomial.C ((2 : ℝ) ^ t))) * (∏ j ∈ Finset.Icc 1 n, (∑ i ∈ Finset.range n, (Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X) ^ i))).coeff (n - 1) = ∑ k ∈ Finset.Icc 1 n, ((-∏ t ∈ Finset.Icc 1 (n - 1), (Polynomial.C (3 : ℝ) * Polynomial.X - Polynomial.C ((2 : ℝ) ^ t))).eval ((8 : ℝ) * 2 ^ k)⁻¹ * (∏ j ∈ (Finset.Icc 1 n).erase k, (1 - ((8 : ℝ) * 2 ^ j) / ((8 : ℝ) * 2 ^ k)))⁻¹) * ((8 : ℝ) * 2 ^ k) ^ (n - 1) := by
      nth_rw 1 [hid]
      rw [Finset.sum_mul, Polynomial.finsetSum_coeff]
      refine Finset.sum_congr rfl (fun k hk => ?_)
      rw [mul_assoc, Polynomial.coeff_C_mul, hTP k hk]
    -- (4) and it is an integer, since Qt * P has integer coefficients
    have hmap : (-∏ t ∈ Finset.Icc 1 (n - 1), (Polynomial.C (3 : ℝ) * Polynomial.X - Polynomial.C ((2 : ℝ) ^ t))) * (∏ j ∈ Finset.Icc 1 n, (∑ i ∈ Finset.range n, (Polynomial.C ((8 : ℝ) * 2 ^ j) * Polynomial.X) ^ i)) = Polynomial.map (Int.castRingHom ℝ) ((-∏ t ∈ Finset.Icc 1 (n - 1), (Polynomial.C (3 : ℤ) * Polynomial.X - Polynomial.C ((2 : ℤ) ^ t))) * (∏ j ∈ Finset.Icc 1 n, ∑ i ∈ Finset.range n, (Polynomial.C ((8 : ℤ) * 2 ^ j) * Polynomial.X) ^ i)) := by
      simp [Polynomial.map_prod, Polynomial.map_sum, Polynomial.C_mul, Polynomial.C_pow, map_ofNat]
    -- (5) C_k r_k^(n-1) = 3^(n-1) A(n,k)
    have hcard : (Finset.Icc 1 (n - 1)).card = n - 1 := by rw [Nat.card_Icc]; omega
    have hterm : ∀ k ∈ Finset.Icc 1 n, ((-∏ t ∈ Finset.Icc 1 (n - 1), (Polynomial.C (3 : ℝ) * Polynomial.X - Polynomial.C ((2 : ℝ) ^ t))).eval ((8 : ℝ) * 2 ^ k)⁻¹ * (∏ j ∈ (Finset.Icc 1 n).erase k, (1 - ((8 : ℝ) * 2 ^ j) / ((8 : ℝ) * 2 ^ k)))⁻¹) * ((8 : ℝ) * 2 ^ k) ^ (n - 1) = (3 : ℝ) ^ (n - 1) * (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) := by
      intro k hk
      have hq : ∀ t : ℕ, (3 : ℝ) * ((8 : ℝ) * 2 ^ k)⁻¹ - 2 ^ t = ((8 : ℝ) * 2 ^ k)⁻¹ * (3 * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) := fun t => by
        have := hr0 k
        rw [pow_add]; field_simp
      have hw : ∀ j : ℕ, ((8 : ℝ) * 2 ^ j) / ((8 : ℝ) * 2 ^ k) = (2 : ℝ) ^ ((j : ℤ) - (k : ℤ)) := fun j => by
        rw [zpow_sub₀ two_ne_zero, zpow_natCast, zpow_natCast]
        field_simp
      have hrr : (((8 : ℝ) * 2 ^ k)⁻¹) ^ (n - 1) * ((8 : ℝ) * 2 ^ k) ^ (n - 1) = 1 := by
        rw [← mul_pow, inv_mul_cancel₀ (hr0 k), one_pow]
      simp only [Polynomial.eval_neg, Polynomial.eval_prod, Polynomial.eval_sub, Polynomial.eval_mul, Polynomial.eval_C,
        Polynomial.eval_X]
      rw [Finset.prod_congr rfl (fun t _ => hq t), Finset.prod_mul_distrib, Finset.prod_mul_distrib, Finset.prod_const,
        Finset.prod_const, hcard]
      simp only [hw]
      linear_combination (-((3 : ℝ) ^ (n - 1) * ∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) *
        (∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - (k : ℤ))))⁻¹) * hrr
    refine ⟨((-∏ t ∈ Finset.Icc 1 (n - 1), (Polynomial.C (3 : ℤ) * Polynomial.X - Polynomial.C ((2 : ℤ) ^ t))) * (∏ j ∈ Finset.Icc 1 n, ∑ i ∈ Finset.range n, (Polynomial.C ((8 : ℤ) * 2 ^ j) * Polynomial.X) ^ i)).coeff (n - 1), ?_⟩
    have hc : ((((-∏ t ∈ Finset.Icc 1 (n - 1), (Polynomial.C (3 : ℤ) * Polynomial.X - Polynomial.C ((2 : ℤ) ^ t))) * (∏ j ∈ Finset.Icc 1 n, ∑ i ∈ Finset.range n, (Polynomial.C ((8 : ℤ) * 2 ^ j) * Polynomial.X) ^ i)).coeff (n - 1) : ℤ) : ℝ) = (Polynomial.map (Int.castRingHom ℝ) ((-∏ t ∈ Finset.Icc 1 (n - 1), (Polynomial.C (3 : ℤ) * Polynomial.X - Polynomial.C ((2 : ℤ) ^ t))) * (∏ j ∈ Finset.Icc 1 n, ∑ i ∈ Finset.range n, (Polynomial.C ((8 : ℤ) * 2 ^ j) * Polynomial.X) ^ i))).coeff (n - 1) := by
      rw [Polynomial.coeff_map]; simp
    rw [hc, ← hmap, hQP, Finset.mul_sum]
    exact Finset.sum_congr rfl hterm
  have hW3 : ∀ n : ℕ, ∏ k ∈ Finset.Icc 1 n, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ k) = (∏ k ∈ Finset.Icc 1 n, ((3 : ℝ) - 8 * 2 ^ k)) * ((3 : ℝ) ^ n)⁻¹ := by
    intro n
    rw [Finset.prod_congr rfl (fun k _ => (by ring : (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ k) = ((3 : ℝ) - 8 * 2 ^ k) * (3 : ℝ)⁻¹)),
      Finset.prod_mul_distrib, Finset.prod_const, Nat.card_Icc, Nat.add_sub_cancel, inv_pow]
  refine ⟨fun n => if h : 1 ≤ n then 3 * (Nat.factorial (n - 2) : ℤ) * (∏ k ∈ Finset.Icc 1 n, ((3 : ℤ) - 8 * 2 ^ k)) *
      (∏ k ∈ Finset.Icc ((n + 1) / 2) n, ((1 : ℤ) - 2 ^ k)) * Classical.choose (key n h) else 0, fun n hn => ?_⟩
  simp only [dif_pos hn]
  push_cast
  rw [Classical.choose_spec (key n hn), hW3 n]
  have h9 : (9 : ℝ) ^ n = 3 * (3 : ℝ) ^ (n - 1) * (3 : ℝ) ^ n := by
    rw [show (9 : ℝ) = 3 * 3 by norm_num, mul_pow, mul_comm (3 : ℝ) _, ← pow_succ, Nat.sub_add_cancel hn]
  have h3 : ((3 : ℝ) ^ n)⁻¹ * (3 : ℝ) ^ n = 1 := inv_mul_cancel₀ (by positivity)
  rw [h9]
  linear_combination (-(3 : ℝ) * (Nat.factorial (n - 2) : ℝ) * (∏ k ∈ Finset.Icc 1 n, ((3 : ℝ) - 8 * 2 ^ k)) *
      (∏ k ∈ Finset.Icc ((n + 1) / 2) n, ((1 : ℝ) - 2 ^ k)) * ((3 : ℝ) ^ (n - 1) * (∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k)))))) * h3
