import Mathlib

theorem pf_test : ∀ n : ℕ, 1 ≤ n → ∀ m : ℕ, 1 ≤ m → (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((m : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (m : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (m : ℕ)))⁻¹) = ((∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (k + m))⁻¹) + ∑ i ∈ Finset.Icc 1 (n - 1), (∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (((8 / 3 : ℝ) * (2 : ℝ) ^ k) ^ i)⁻¹) * (((2 : ℝ) ^ m) ^ i)⁻¹) := by
  intro n hn m hm
  -- General partial fractions, from Mathlib's Lagrange interpolation.
  have lag : ∀ (s : Finset ℕ) (p : ℕ → ℝ) (Q : Polynomial ℝ), (∀ k ∈ s, p k ≠ 0) → Set.InjOn p s →
    Q.degree < s.card → ∀ x : ℝ, (∀ k ∈ s, 1 - p k * x ≠ 0) →
    Q.eval x * ∏ k ∈ s, (1 - p k * x)⁻¹ =
      ∑ k ∈ s, Q.eval (p k)⁻¹ * (∏ j ∈ s.erase k, (1 - p j / p k))⁻¹ * (1 - p k * x)⁻¹ := by
    intro s p Q hp hinj hdeg x hx
    have hinj' : Set.InjOn (fun k => (p k)⁻¹) s := by
      intro a ha b hb hab
      exact hinj ha hb (inv_injective hab)
    have hxv : ∀ k ∈ s, x ≠ (p k)⁻¹ := by
      intro k hk hxk
      apply hx k hk
      rw [hxk, mul_inv_cancel₀ (hp k hk), sub_self]
    have hQ := Lagrange.eq_interpolate hinj' hdeg
    have hev := Lagrange.eval_interpolate_not_at_node (s := s) (v := fun k => (p k)⁻¹) (fun i => Q.eval (p i)⁻¹) hxv
    rw [← hQ, Lagrange.eval_nodal] at hev
    have hfac : ∀ k ∈ s, (1 - p k * x)⁻¹ = (x - (p k)⁻¹)⁻¹ * (-(p k)⁻¹) := by
      intro k hk
      have h1 := hp k hk
      have h3 : (x - (p k)⁻¹) * (-(p k)) = 1 - p k * x := by
        rw [sub_mul, mul_neg, mul_neg, inv_mul_cancel₀ h1]; ring
      rw [← h3, mul_inv, inv_neg]
    rw [Finset.prod_congr rfl hfac, Finset.prod_mul_distrib, hev]
    have hne : ∏ i ∈ s, (x - (p i)⁻¹) ≠ 0 := Finset.prod_ne_zero_iff.mpr (fun i hi => sub_ne_zero.mpr (hxv i hi))
    rw [Finset.prod_inv_distrib, mul_assoc, ← mul_assoc (∑ i ∈ s, _), mul_comm (∑ i ∈ s, _), ← mul_assoc, ← mul_assoc,
      mul_inv_cancel₀ hne, one_mul, Finset.sum_mul]
    refine Finset.sum_congr rfl (fun k hk => ?_)
    rw [Lagrange.nodalWeight, ← Finset.mul_prod_erase s (fun i => -(p i)⁻¹) hk]
    have hj : ∀ j ∈ s.erase k, ((p k)⁻¹ - (p j)⁻¹)⁻¹ * -(p j)⁻¹ = (1 - p j / p k)⁻¹ := by
      intro j hj
      have hjs := Finset.mem_of_mem_erase hj
      have hjk := Finset.ne_of_mem_erase hj
      have hpj := hp j hjs
      have hpk := hp k hk
      have hne : p j ≠ p k := fun h => hjk (hinj hjs hk h)
      have hsub : p k - p j ≠ 0 := sub_ne_zero.mpr (Ne.symm hne)
      field_simp
      ring
    calc (∏ j ∈ s.erase k, ((p k)⁻¹ - (p j)⁻¹)⁻¹) * (x - (p k)⁻¹)⁻¹ * Q.eval (p k)⁻¹ *
          (-(p k)⁻¹ * ∏ j ∈ s.erase k, -(p j)⁻¹)
        = Q.eval (p k)⁻¹ * (∏ j ∈ s.erase k, (((p k)⁻¹ - (p j)⁻¹)⁻¹ * -(p j)⁻¹)) * ((x - (p k)⁻¹)⁻¹ * -(p k)⁻¹) := by
          rw [Finset.prod_mul_distrib]; ring
      _ = Q.eval (p k)⁻¹ * (∏ j ∈ s.erase k, (1 - p j / p k))⁻¹ * (1 - p k * x)⁻¹ := by
          rw [Finset.prod_congr rfl hj, ← Finset.prod_inv_distrib, hfac k hk]
  have hx2 : (2 : ℝ) ≤ (2 : ℝ) ^ m := by
    calc (2 : ℝ) = 2 ^ 1 := (pow_one 2).symm
      _ ≤ 2 ^ m := pow_le_pow_right₀ (by norm_num) hm
  have hx0 : (2 : ℝ) ^ m ≠ 0 := by positivity
  have hp0 : ∀ k : ℕ, (8 / 3 : ℝ) * 2 ^ k ≠ 0 := fun k => by positivity
  have hpx : ∀ k : ℕ, 1 - (8 / 3 : ℝ) * 2 ^ k * 2 ^ m ≠ 0 := by
    intro k
    have h1 : (1 : ℝ) ≤ 2 ^ k := one_le_pow₀ (by norm_num)
    nlinarith
  have hinj : Set.InjOn (fun k : ℕ => (8 / 3 : ℝ) * 2 ^ k) (Finset.Icc 1 n : Set ℕ) := by
    intro a _ b _ hab
    have h : (2 : ℝ) ^ a = 2 ^ b := by
      have := hab; simp only at this
      exact mul_left_cancel₀ (by norm_num : (8 / 3 : ℝ) ≠ 0) this
    exact pow_right_injective₀ (by norm_num : (0 : ℝ) < 2) (by norm_num) h
  have hdeg : (-∏ t ∈ Finset.Icc 1 (n - 1), (Polynomial.X - Polynomial.C ((2 : ℝ) ^ t))).degree < ((Finset.Icc 1 n).card : WithBot ℕ) := by
    rw [Polynomial.degree_neg, Polynomial.degree_prod]
    simp only [Polynomial.degree_X_sub_C, Finset.sum_const, Nat.card_Icc]
    rw [show n - 1 + 1 - 1 = n - 1 by omega, show n + 1 - 1 = n by omega, nsmul_one]
    exact_mod_cast (by omega : n - 1 < n)
  have hL := lag (Finset.Icc 1 n) (fun k => (8 / 3 : ℝ) * 2 ^ k) (-∏ t ∈ Finset.Icc 1 (n - 1), (Polynomial.X - Polynomial.C ((2 : ℝ) ^ t)))
    (fun k _ => hp0 k) hinj hdeg ((2 : ℝ) ^ m) (fun k _ => hpx k)
  simp only [Polynomial.eval_neg, Polynomial.eval_prod, Polynomial.eval_sub, Polynomial.eval_X, Polynomial.eval_C] at hL
  have hcard : (Finset.Icc 1 (n - 1)).card = n - 1 := by rw [Nat.card_Icc]; omega
  -- geometric sums
  have hgeo : ∀ u : ℝ, u ≠ 0 → 1 - u ≠ 0 → ∀ N : ℕ, (1 - u)⁻¹ + ∑ i ∈ Finset.Icc 1 N, (u ^ i)⁻¹ = (u ^ N)⁻¹ * (1 - u)⁻¹ := by
    intro u hu hu1 N
    induction N with
    | zero => simp
    | succ N ih =>
      rw [Finset.sum_Icc_succ_top (by omega), ← add_assoc, ih]
      have hN : u ^ N ≠ 0 := pow_ne_zero _ hu
      field_simp
      ring
  -- the left side, in terms of the Lagrange data
  have hz1 : ∀ k : ℕ, (2 : ℝ) ^ ((k : ℤ) - (m : ℤ)) = 2 ^ k * ((2 : ℝ) ^ m)⁻¹ := fun k => by
    rw [zpow_sub₀ two_ne_zero, zpow_natCast, zpow_natCast, div_eq_mul_inv]
  have hz2 : ∀ k : ℕ, (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (m : ℤ)) = ((8 / 3 : ℝ) * 2 ^ k) * (2 : ℝ) ^ m := fun k => by
    rw [zpow_add₀ two_ne_zero, zpow_natCast, zpow_natCast, mul_assoc]
  have hz3 : (8 / 3 : ℝ) * (2 : ℝ) ^ ((m : ℤ) + (n : ℤ)) = ((8 / 3 : ℝ) * 2 ^ n) * (2 : ℝ) ^ m := by
    rw [zpow_add₀ two_ne_zero, zpow_natCast, zpow_natCast, mul_comm ((2 : ℝ) ^ m), mul_assoc]
  have hsplit : ∏ k ∈ Finset.Icc 1 n, (1 - ((8 / 3 : ℝ) * 2 ^ k) * (2 : ℝ) ^ m)⁻¹ = (∏ k ∈ Finset.Icc 1 (n - 1), (1 - ((8 / 3 : ℝ) * 2 ^ k) * (2 : ℝ) ^ m)⁻¹) * (1 - ((8 / 3 : ℝ) * 2 ^ n) * (2 : ℝ) ^ m)⁻¹ := by
    have hn' : n = n - 1 + 1 := by omega
    conv_lhs => rw [hn']
    rw [Finset.prod_Icc_succ_top (by omega), ← hn']
  have hfac : ∀ k : ℕ, 1 - 2 ^ k * ((2 : ℝ) ^ m)⁻¹ = ((2 : ℝ) ^ m)⁻¹ * ((2 : ℝ) ^ m - (2 : ℝ) ^ k) := fun k => by
    rw [mul_sub, inv_mul_cancel₀ hx0]; ring
  have hLHS : (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((m : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (m : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (m : ℕ)))⁻¹) = (((2 : ℝ) ^ m) ^ (n - 1))⁻¹ * ((-∏ t ∈ Finset.Icc 1 (n - 1), ((2 : ℝ) ^ m - (2 : ℝ) ^ t)) * ∏ k ∈ Finset.Icc 1 n, (1 - ((8 / 3 : ℝ) * 2 ^ k) * (2 : ℝ) ^ m)⁻¹) := by
    simp only [hz1, hz2, hz3]
    rw [Finset.prod_mul_distrib, hsplit, Finset.prod_congr rfl (fun k _ => hfac k), Finset.prod_mul_distrib,
      Finset.prod_const, hcard, inv_pow]
    ring
  -- the right side
  have hpk : ∀ k : ℕ, (8 / 3 : ℝ) * 2 ^ (k + m) = ((8 / 3 : ℝ) * 2 ^ k) * (2 : ℝ) ^ m := fun k => by rw [pow_add, mul_assoc]
  have hswap : ∑ i ∈ Finset.Icc 1 (n - 1), (∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (((8 / 3 : ℝ) * (2 : ℝ) ^ k) ^ i)⁻¹) * (((2 : ℝ) ^ m) ^ i)⁻¹ = ∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * ∑ i ∈ Finset.Icc 1 (n - 1), ((((8 / 3 : ℝ) * 2 ^ k) * (2 : ℝ) ^ m) ^ i)⁻¹ := by
    simp only [Finset.sum_mul, Finset.mul_sum]
    rw [Finset.sum_comm]
    refine Finset.sum_congr rfl (fun k _ => Finset.sum_congr rfl (fun i _ => ?_))
    rw [mul_pow, mul_inv]; ring
  have hRHS : ((∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (k + m))⁻¹) + ∑ i ∈ Finset.Icc 1 (n - 1), (∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (((8 / 3 : ℝ) * (2 : ℝ) ^ k) ^ i)⁻¹) * (((2 : ℝ) ^ m) ^ i)⁻¹) = (∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * ((((8 / 3 : ℝ) * 2 ^ k) * (2 : ℝ) ^ m) ^ (n - 1))⁻¹ * (1 - ((8 / 3 : ℝ) * 2 ^ k) * (2 : ℝ) ^ m)⁻¹) := by
    simp only [hpk]
    rw [hswap, ← Finset.sum_add_distrib]
    refine Finset.sum_congr rfl (fun k hk => ?_)
    rw [← mul_add, hgeo _ (mul_ne_zero (hp0 k) hx0) (hpx k) (n - 1)]
    ring
  -- matching the coefficients
  have hcoef : ∀ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (((8 / 3 : ℝ) * 2 ^ k) ^ (n - 1))⁻¹ = (-∏ t ∈ Finset.Icc 1 (n - 1), (((8 / 3 : ℝ) * 2 ^ k)⁻¹ - (2 : ℝ) ^ t)) * (∏ j ∈ (Finset.Icc 1 n).erase k, (1 - ((8 / 3 : ℝ) * 2 ^ j) / ((8 / 3 : ℝ) * 2 ^ k)))⁻¹ := by
    intro k hk
    have hq : ∀ t : ℕ, ((8 / 3 : ℝ) * 2 ^ k)⁻¹ - (2 : ℝ) ^ t = ((8 / 3 : ℝ) * 2 ^ k)⁻¹ * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k)) := fun t => by
      rw [mul_sub, mul_one, pow_add, show ((8 / 3 : ℝ) * 2 ^ k)⁻¹ * ((8 / 3 : ℝ) * (2 ^ t * 2 ^ k)) = 2 ^ t * (((8 / 3 : ℝ) * 2 ^ k)⁻¹ * ((8 / 3 : ℝ) * 2 ^ k)) by ring,
        inv_mul_cancel₀ (hp0 k), mul_one]
    have hw : ∀ j : ℕ, ((8 / 3 : ℝ) * 2 ^ j) / ((8 / 3 : ℝ) * 2 ^ k) = (2 : ℝ) ^ ((j : ℤ) - (k : ℤ)) := fun j => by
      rw [zpow_sub₀ two_ne_zero, zpow_natCast, zpow_natCast]
      field_simp
    rw [Finset.prod_congr rfl (fun t _ => hq t), Finset.prod_mul_distrib, Finset.prod_const, hcard, inv_pow]
    simp only [hw]
    ring
  calc (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((m : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (m : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (m : ℕ)))⁻¹) = (((2 : ℝ) ^ m) ^ (n - 1))⁻¹ * ((-∏ t ∈ Finset.Icc 1 (n - 1), ((2 : ℝ) ^ m - (2 : ℝ) ^ t)) * ∏ k ∈ Finset.Icc 1 n, (1 - ((8 / 3 : ℝ) * 2 ^ k) * (2 : ℝ) ^ m)⁻¹) := hLHS
    _ = (((2 : ℝ) ^ m) ^ (n - 1))⁻¹ * (∑ k ∈ Finset.Icc 1 n, (-∏ t ∈ Finset.Icc 1 (n - 1), (((8 / 3 : ℝ) * 2 ^ k)⁻¹ - (2 : ℝ) ^ t)) * (∏ j ∈ (Finset.Icc 1 n).erase k, (1 - ((8 / 3 : ℝ) * 2 ^ j) / ((8 / 3 : ℝ) * 2 ^ k)))⁻¹ * (1 - ((8 / 3 : ℝ) * 2 ^ k) * (2 : ℝ) ^ m)⁻¹) := by rw [hL]
    _ = (∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * ((((8 / 3 : ℝ) * 2 ^ k) * (2 : ℝ) ^ m) ^ (n - 1))⁻¹ * (1 - ((8 / 3 : ℝ) * 2 ^ k) * (2 : ℝ) ^ m)⁻¹) := by
      rw [Finset.mul_sum]
      refine Finset.sum_congr rfl (fun k hk => ?_)
      rw [← hcoef k hk, mul_pow, mul_inv]
      ring
    _ = ((∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (k + m))⁻¹) + ∑ i ∈ Finset.Icc 1 (n - 1), (∑ k ∈ Finset.Icc 1 n, (-(∏ t ∈ Finset.Icc 1 (n - 1), (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (t + k))) / ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - k))) * (((8 / 3 : ℝ) * (2 : ℝ) ^ k) ^ i)⁻¹) * (((2 : ℝ) ^ m) ^ i)⁻¹) := hRHS.symm
