import Mathlib
import Nodes.«erdos-1050--h1-v2».Context

/-! Hole `borwein` of a merged partial proof, as a node (D-12 #5, D-29).
Revised statement (D-8): the parent assembly's own `have borwein` type, with the binder types and
the real-number ascriptions the gate-written statement had dropped. -/

theorem erdos_1050__h1 : ∃ a b : ℕ → ℤ,
    (∀ n : ℕ, (b n : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - a n ≠ 0) ∧
    Filter.Tendsto
      (fun n : ℕ => (b n : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - a n)
      Filter.atTop (nhds 0) := by
  -- Transfer (proved): z = 3/5 - 3T, where z is Borwein's reduced q-harmonic value (q = 2, c = 8/3).
  have transfer : (∑' j : ℕ, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (j + 1))⁻¹) = 3 / 5 - 3 * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) := by
    have hs : Summable (fun n : ℕ => (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) := by
      refine Summable.of_nonneg_of_le (fun n => ?_) (fun n => ?_)
        (summable_geometric_of_lt_one (by norm_num : (0:ℝ) ≤ 1/2) (by norm_num : (1/2:ℝ) < 1))
      · have h1 : (1:ℝ) ≤ 2 ^ n := one_le_pow₀ (by norm_num)
        have h2 : (2:ℝ) ^ (n + 3) = 8 * 2 ^ n := by ring
        apply div_nonneg zero_le_one
        rw [h2]; linarith
      · have h1 : (1:ℝ) ≤ 2 ^ n := one_le_pow₀ (by norm_num)
        have h2 : (2:ℝ) ^ (n + 3) = 8 * 2 ^ n := by ring
        rw [h2, one_div_pow]
        exact one_div_le_one_div_of_le (by positivity) (by linarith)
    have hterm : ∀ j : ℕ, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (j + 1))⁻¹
        = -3 * ((1 : ℝ) / ((2 : ℝ) ^ ((j + 1) + 3) - 3)) := by
      intro j
      have hp : (2 : ℝ) ≤ (2 : ℝ) ^ (j + 1) := by
        calc (2 : ℝ) = 2 ^ 1 := (pow_one 2).symm
          _ ≤ 2 ^ (j + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
      have hexp : (2 : ℝ) ^ ((j + 1) + 3) = 8 * 2 ^ (j + 1) := by ring
      rw [hexp]
      have hd2 : (1 : ℝ) - 8 / 3 * 2 ^ (j + 1) ≠ 0 := ne_of_lt (by nlinarith [hp])
      have hd1 : (8 : ℝ) * 2 ^ (j + 1) - 3 ≠ 0 := ne_of_gt (by nlinarith [hp])
      rw [inv_eq_one_div, mul_one_div, div_eq_div_iff hd2 hd1]
      ring
    rw [tsum_congr hterm, tsum_mul_left, hs.tsum_eq_zero_add]
    norm_num
    ring
  -- Non-vanishing of the clearing factor W(n) (proved).
  have w_ne : ∀ n : ℕ, 1 ≤ n → ((Nat.factorial (n - 2) : ℝ) * (∏ k ∈ Finset.Icc 1 n, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ k)) * (∏ k ∈ Finset.Icc ((n + 1) / 2) n, (1 - (2 : ℝ) ^ k))) ≠ 0 := by
    intro n hn
    refine mul_ne_zero (mul_ne_zero (by exact_mod_cast Nat.factorial_ne_zero _) ?_) ?_
    · rw [Finset.prod_ne_zero_iff]
      intro k hk
      have hk1 : 1 ≤ k := (Finset.mem_Icc.mp hk).1
      have hp : (2 : ℝ) ≤ (2 : ℝ) ^ k := by
        calc (2 : ℝ) = 2 ^ 1 := (pow_one 2).symm
          _ ≤ 2 ^ k := pow_le_pow_right₀ (by norm_num) hk1
      nlinarith
    · rw [Finset.prod_ne_zero_iff]
      intro k hk
      have hk1 : 1 ≤ k := by have := (Finset.mem_Icc.mp hk).1; omega
      have hp : (2 : ℝ) ≤ (2 : ℝ) ^ k := by
        calc (2 : ℝ) = 2 ^ 1 := (pow_one 2).symm
          _ ≤ 2 ^ k := pow_le_pow_right₀ (by norm_num) hk1
      intro h; linarith
  -- Non-vanishing of the error series E(n) (proved: each term has sign (-1)^(n-1)).
  have e_ne : ∀ n : ℕ, 1 ≤ n → (∑' j : ℕ, (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹)) ≠ 0 := by
    -- Ported from lean-gallery (Trevor Morris, Apache-2.0), Approximants.lean, Eterm_ne_zero.
    intro n hn
    have two_le_zpow : ∀ a : ℤ, 1 ≤ a → (2 : ℝ) ≤ (2 : ℝ) ^ a := fun a ha => by
      calc (2 : ℝ) = (2 : ℝ) ^ (1 : ℤ) := by norm_num
        _ ≤ (2 : ℝ) ^ a := zpow_le_zpow_right₀ (by norm_num) ha
    have inv_le : ∀ a : ℤ, 1 ≤ a → |(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ a)⁻¹| ≤ (2 : ℝ) ^ (-a) := fun a ha => by
      have hqa := two_le_zpow a ha
      have hqpos : (0 : ℝ) < (2 : ℝ) ^ a := zpow_pos (by norm_num) a
      have hge : (2 : ℝ) ^ a ≤ (8 / 3 : ℝ) * (2 : ℝ) ^ a - 1 := by nlinarith
      have habs : |(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ a)⁻¹| = ((8 / 3 : ℝ) * (2 : ℝ) ^ a - 1)⁻¹ := by
        rw [abs_inv]; congr 1; rw [abs_of_neg (by linarith)]; ring
      rw [habs, zpow_neg]
      exact inv_anti₀ hqpos hge
    have lead_neg : ∀ a : ℤ, 1 ≤ a → (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ a)⁻¹ < 0 := fun a ha => by
      have h2 := two_le_zpow a ha
      have hneg : (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ a) < 0 := by nlinarith
      exact inv_lt_zero.mpr hneg
    have factor_neg : ∀ k m : ℕ, 1 ≤ k → k < m →
        (1 - (2 : ℝ) ^ ((k : ℤ) - m)) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + m))⁻¹ < 0 := by
      intro k m hk hkm
      have hnum : 0 < 1 - (2 : ℝ) ^ ((k : ℤ) - m) := by
        have hle : (2 : ℝ) ^ ((k : ℤ) - m) ≤ (2 : ℝ) ^ (-1 : ℤ) :=
          zpow_le_zpow_right₀ (by norm_num) (by omega)
        have heq : (2 : ℝ) ^ (-1 : ℤ) = 1 / 2 := by rw [zpow_neg, zpow_one]; norm_num
        rw [heq] at hle; linarith
      exact mul_neg_of_pos_of_neg hnum (lead_neg _ (by omega))
    have factor_le : ∀ k m : ℕ, 1 ≤ k → k < m →
        |(1 - (2 : ℝ) ^ ((k : ℤ) - m)) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + m))⁻¹| ≤ 1 := by
      intro k m hk hkm
      rw [abs_mul]
      have h1 : |1 - (2 : ℝ) ^ ((k : ℤ) - m)| ≤ 1 := by
        have hle1 : (2 : ℝ) ^ ((k : ℤ) - m) ≤ 1 := by
          calc (2 : ℝ) ^ ((k : ℤ) - m) ≤ (2 : ℝ) ^ (0 : ℤ) := zpow_le_zpow_right₀ (by norm_num) (by omega)
            _ = 1 := by norm_num
        have hpos : 0 < (2 : ℝ) ^ ((k : ℤ) - m) := zpow_pos (by norm_num) _
        rw [abs_of_nonneg (by linarith)]; linarith
      have h2 := inv_le ((k : ℤ) + m) (by omega)
      have h3 : (2 : ℝ) ^ (-((k : ℤ) + m)) ≤ 1 := zpow_le_one_of_nonpos₀ (by norm_num) (by omega)
      calc _ ≤ 1 * 1 := mul_le_mul h1 (h2.trans h3) (abs_nonneg _) (by norm_num)
        _ = 1 := by ring
    -- each term is bounded by (1/2)^j
    have term_le : ∀ j : ℕ, |(-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹)| ≤ (1 / 2 : ℝ) ^ j := by
      intro j
      rw [abs_mul, abs_neg]
      have hlead := inv_le (((n + j : ℕ) : ℤ) + n) (by omega)
      have hprod : |∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹| ≤ 1 := by
        rw [Finset.abs_prod]
        apply Finset.prod_le_one (fun k _ => abs_nonneg _)
        intro k hk
        rw [Finset.mem_Icc] at hk
        exact factor_le k (n + j) hk.1 (by omega)
      have hexp : (2 : ℝ) ^ (-(((n + j : ℕ) : ℤ) + n)) ≤ (2 : ℝ) ^ (-(j : ℤ)) := by
        apply zpow_le_zpow_right₀ (by norm_num); push_cast; omega
      have hj : (2 : ℝ) ^ (-(j : ℤ)) = (1 / 2 : ℝ) ^ j := by
        rw [zpow_neg, zpow_natCast, one_div, inv_pow]
      calc _ ≤ (2 : ℝ) ^ (-(((n + j : ℕ) : ℤ) + n)) * 1 :=
            mul_le_mul hlead hprod (abs_nonneg _) (le_of_lt (zpow_pos (by norm_num) _))
        _ ≤ (1 / 2 : ℝ) ^ j := by rw [mul_one, ← hj]; exact hexp
    have hsum : Summable (fun j : ℕ => (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹)) := by
      apply Summable.of_norm_bounded (g := fun j => (1 / 2 : ℝ) ^ j)
      · exact summable_geometric_of_lt_one (by norm_num) (by norm_num)
      · intro j; rw [Real.norm_eq_abs]; exact term_le j
    have hpos : ∀ j : ℕ, 0 < (-1 : ℝ) ^ (n - 1) * (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹) := by
      intro j
      have hL := lead_neg (((n + j : ℕ) : ℤ) + n) (by omega)
      have hcard : (Finset.Icc 1 (n - 1)).card = n - 1 := by rw [Nat.card_Icc, Nat.add_sub_cancel]
      have h1 : (-1 : ℝ) ^ (n - 1) = ∏ _k ∈ Finset.Icc 1 (n - 1), (-1 : ℝ) := by
        rw [Finset.prod_const, hcard]
      have hP : 0 < (-1 : ℝ) ^ (n - 1) * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹ := by
        rw [h1, ← Finset.prod_mul_distrib]
        apply Finset.prod_pos
        intro k hk
        rw [Finset.mem_Icc] at hk
        have hf := factor_neg k (n + j) hk.1 (by omega)
        linarith
      have hnegL : (0 : ℝ) < -(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ := by linarith
      have := mul_pos hnegL hP
      linarith [this, show (-1 : ℝ) ^ (n - 1) * (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹) = -(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ((-1 : ℝ) ^ (n - 1) * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹) by ring]
    have hp : 0 < ∑' j : ℕ, (-1 : ℝ) ^ (n - 1) * (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹) :=
      (hsum.mul_left _).tsum_pos (fun j => le_of_lt (hpos j)) 0 (hpos 0)
    rw [tsum_mul_left] at hp
    intro h0
    rw [h0, mul_zero] at hp
    exact lt_irrefl 0 hp
  -- Decay (Borwein Lemma 4, proved): the cleared error 9^n W(n) E(n) tends to 0.
  have decay : Filter.Tendsto (fun n : ℕ => (9 : ℝ) ^ n * ((Nat.factorial (n - 2) : ℝ) * (∏ k ∈ Finset.Icc 1 n, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ k)) * (∏ k ∈ Finset.Icc ((n + 1) / 2) n, (1 - (2 : ℝ) ^ k))) * (∑' j : ℕ, (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹))) Filter.atTop (nhds 0) := by
    -- Ported from lean-gallery (Trevor Morris, Apache-2.0), Approximants.lean:
    -- Iterm_abs_le_geom, Eterm_abs_le', Wterm_abs_le, cleared_error_le, combine_asymptotic.
    have two_le_pow : ∀ k : ℕ, 1 ≤ k → (2 : ℝ) ≤ (2 : ℝ) ^ k := fun k hk => by
      calc (2 : ℝ) = 2 ^ 1 := (pow_one 2).symm
        _ ≤ 2 ^ k := pow_le_pow_right₀ (by norm_num) hk
    have two_le_zpow : ∀ a : ℤ, 1 ≤ a → (2 : ℝ) ≤ (2 : ℝ) ^ a := fun a ha => by
      calc (2 : ℝ) = (2 : ℝ) ^ (1 : ℤ) := by norm_num
        _ ≤ (2 : ℝ) ^ a := zpow_le_zpow_right₀ (by norm_num) ha
    have inv_le : ∀ a : ℤ, 1 ≤ a → |(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ a)⁻¹| ≤ (2 : ℝ) ^ (-a) := fun a ha => by
      have hqa := two_le_zpow a ha
      have hqpos : (0 : ℝ) < (2 : ℝ) ^ a := zpow_pos (by norm_num) a
      have hge : (2 : ℝ) ^ a ≤ (8 / 3 : ℝ) * (2 : ℝ) ^ a - 1 := by nlinarith
      have habs : |(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ a)⁻¹| = ((8 / 3 : ℝ) * (2 : ℝ) ^ a - 1)⁻¹ := by
        rw [abs_inv]; congr 1; rw [abs_of_neg (by linarith)]; ring
      rw [habs, zpow_neg]
      exact inv_anti₀ hqpos hge
    have factor_abs_le : ∀ k m : ℕ, 1 ≤ k → k < m →
        |(1 - (2 : ℝ) ^ ((k : ℤ) - m)) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + m))⁻¹| ≤ ((2 : ℝ) ^ (k + m))⁻¹ := by
      intro k m hk hkm
      rw [abs_mul]
      have h1 : |1 - (2 : ℝ) ^ ((k : ℤ) - m)| ≤ 1 := by
        have hle1 : (2 : ℝ) ^ ((k : ℤ) - m) ≤ 1 := by
          calc (2 : ℝ) ^ ((k : ℤ) - m) ≤ (2 : ℝ) ^ (0 : ℤ) := zpow_le_zpow_right₀ (by norm_num) (by omega)
            _ = 1 := by norm_num
        have hpos : 0 < (2 : ℝ) ^ ((k : ℤ) - m) := zpow_pos (by norm_num) _
        rw [abs_of_nonneg (by linarith)]; linarith
      have h2 := inv_le ((k : ℤ) + m) (by omega)
      have h3 : (2 : ℝ) ^ (-((k : ℤ) + m)) = ((2 : ℝ) ^ (k + m))⁻¹ := by
        rw [zpow_neg, ← zpow_natCast (2 : ℝ) (k + m), Nat.cast_add]
      calc _ ≤ 1 * (2 : ℝ) ^ (-((k : ℤ) + m)) := mul_le_mul h1 h2 (abs_nonneg _) (by norm_num)
        _ = ((2 : ℝ) ^ (k + m))⁻¹ := by rw [one_mul, h3]
    have exp_identity : ∀ n : ℕ, 1 ≤ n → ∀ m : ℕ, (m + n) + ∑ k ∈ Finset.Icc 1 (n - 1), (k + m)
        = (n + ∑ k ∈ Finset.Icc 1 (n - 1), k) + n * m := by
      intro n hn m
      rw [Finset.sum_add_distrib, Finset.sum_const, Nat.card_Icc, Nat.add_sub_cancel, smul_eq_mul]
      have hmul : (n - 1) * m + m = n * m := by
        rw [Nat.sub_one_mul, Nat.sub_add_cancel (Nat.le_mul_of_pos_left m hn)]
      omega
    have I_geom : ∀ n m : ℕ, 1 ≤ n → n ≤ m →
        |(-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((m : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - m)) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + m))⁻¹)| ≤ ((2 : ℝ) ^ (n + (∑ k ∈ Finset.Icc 1 (n - 1), k)))⁻¹ * (((2 : ℝ) ^ n)⁻¹) ^ m := by
      intro n m hn hnm
      rw [abs_mul, abs_neg]
      have hlead : |(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((m : ℤ) + n))⁻¹| ≤ ((2 : ℝ) ^ (m + n))⁻¹ := by
        have h := inv_le ((m : ℤ) + n) (by omega)
        have he : (2 : ℝ) ^ (-((m : ℤ) + n)) = ((2 : ℝ) ^ (m + n))⁻¹ := by
          rw [zpow_neg, ← zpow_natCast (2 : ℝ) (m + n), Nat.cast_add]
        rwa [he] at h
      have hprod : |∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - m)) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + m))⁻¹|
          ≤ ∏ k ∈ Finset.Icc 1 (n - 1), ((2 : ℝ) ^ (k + m))⁻¹ := by
        rw [Finset.abs_prod]
        apply Finset.prod_le_prod (fun k _ => abs_nonneg _)
        intro k hk; rw [Finset.mem_Icc] at hk
        exact factor_abs_le k m hk.1 (by omega)
      refine (mul_le_mul hlead hprod (abs_nonneg _) (le_of_lt (inv_pos.mpr (pow_pos (by norm_num) _)))).trans (le_of_eq ?_)
      have hL : ((2 : ℝ) ^ (m + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), ((2 : ℝ) ^ (k + m))⁻¹
          = ((2 : ℝ) ^ ((m + n) + ∑ k ∈ Finset.Icc 1 (n - 1), (k + m)))⁻¹ := by
        rw [Finset.prod_inv_distrib, Finset.prod_pow_eq_pow_sum, ← mul_inv, ← pow_add]
      have hR : ((2 : ℝ) ^ (n + (∑ k ∈ Finset.Icc 1 (n - 1), k)))⁻¹ * (((2 : ℝ) ^ n)⁻¹) ^ m
          = ((2 : ℝ) ^ ((n + (∑ k ∈ Finset.Icc 1 (n - 1), k)) + n * m))⁻¹ := by
        rw [inv_pow, ← pow_mul, ← mul_inv, ← pow_add]
      rw [hL, hR, exp_identity n hn m]
    have E_le : ∀ n : ℕ, 1 ≤ n → |(∑' j : ℕ, (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹))| ≤ 2 * ((2 : ℝ) ^ (n + (∑ k ∈ Finset.Icc 1 (n - 1), k) + n ^ 2))⁻¹ := by
      intro n hn
      set r : ℝ := ((2 : ℝ) ^ n)⁻¹ with hr_def
      set Cn : ℝ := ((2 : ℝ) ^ (n + (∑ k ∈ Finset.Icc 1 (n - 1), k)))⁻¹ with hCn_def
      have hr0 : 0 ≤ r := le_of_lt (inv_pos.mpr (pow_pos (by norm_num) n))
      have hqn2 : (2 : ℝ) ≤ (2 : ℝ) ^ n := two_le_pow n hn
      have hrh : r ≤ 1 / 2 := by rw [hr_def, inv_eq_one_div]; exact one_div_le_one_div_of_le (by norm_num) hqn2
      have hr1 : r < 1 := by linarith
      have hCn0 : 0 ≤ Cn := le_of_lt (inv_pos.mpr (pow_pos (by norm_num) _))
      have hge : ∀ j : ℕ, |(-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹)| ≤ Cn * r ^ (n + j) := fun j =>
        I_geom n (n + j) hn (Nat.le_add_right n j)
      have hsummaj : Summable (fun j : ℕ => Cn * r ^ (n + j)) := by
        simp_rw [pow_add]
        exact ((summable_geometric_of_lt_one hr0 hr1).mul_left _).mul_left _
      have hsummabs : Summable (fun j : ℕ => |(-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹)|) :=
        Summable.of_nonneg_of_le (fun j => abs_nonneg _) hge hsummaj
      have h1 : |(∑' j : ℕ, (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹))| ≤ ∑' j : ℕ, |(-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹)| := by
        have hnorm := norm_tsum_le_tsum_norm (f := fun j : ℕ => (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹))
          (by simpa only [Real.norm_eq_abs] using hsummabs)
        simpa only [Real.norm_eq_abs] using hnorm
      have h2 := hsummabs.tsum_le_tsum hge hsummaj
      have h3 : ∑' j : ℕ, Cn * r ^ (n + j) = Cn * r ^ n * (1 - r)⁻¹ := by
        simp_rw [pow_add, ← mul_assoc]
        rw [tsum_mul_left, tsum_geometric_of_lt_one hr0 hr1]
      have htail : (1 - r)⁻¹ ≤ 2 := by
        calc (1 - r)⁻¹ ≤ (1 / 2 : ℝ)⁻¹ := inv_anti₀ (by norm_num) (by linarith)
          _ = 2 := by norm_num
      have hC : Cn * r ^ n = ((2 : ℝ) ^ (n + (∑ k ∈ Finset.Icc 1 (n - 1), k) + n ^ 2))⁻¹ := by
        rw [hCn_def, hr_def, inv_pow, ← pow_mul, ← mul_inv, ← pow_add, sq]
      have hB : 0 ≤ ((2 : ℝ) ^ (n + (∑ k ∈ Finset.Icc 1 (n - 1), k) + n ^ 2))⁻¹ := le_of_lt (inv_pos.mpr (pow_pos (by norm_num) _))
      calc _ ≤ _ := h1
        _ ≤ _ := h2
        _ = Cn * r ^ n * (1 - r)⁻¹ := h3
        _ = ((2 : ℝ) ^ (n + (∑ k ∈ Finset.Icc 1 (n - 1), k) + n ^ 2))⁻¹ * (1 - r)⁻¹ := by rw [hC]
        _ ≤ ((2 : ℝ) ^ (n + (∑ k ∈ Finset.Icc 1 (n - 1), k) + n ^ 2))⁻¹ * 2 := mul_le_mul_of_nonneg_left htail hB
        _ = 2 * ((2 : ℝ) ^ (n + (∑ k ∈ Finset.Icc 1 (n - 1), k) + n ^ 2))⁻¹ := by ring
    have W_le : ∀ n : ℕ, 1 ≤ n → |((Nat.factorial (n - 2) : ℝ) * (∏ k ∈ Finset.Icc 1 n, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ k)) * (∏ k ∈ Finset.Icc ((n + 1) / 2) n, (1 - (2 : ℝ) ^ k)))| ≤ (Nat.factorial (n - 2) : ℝ) * (8 / 3 : ℝ) ^ n
        * (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k) * (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k) := by
      intro n hn
      have hfac : (0:ℝ) ≤ (Nat.factorial (n-2) : ℝ) := by positivity
      have hqS : (0:ℝ) ≤ (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k) := by positivity
      rw [abs_mul, abs_mul, abs_of_nonneg hfac]
      have hP1 : |∏ k ∈ Finset.Icc 1 n, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ k)| ≤ (8 / 3 : ℝ) ^ n * (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k) := by
        rw [Finset.abs_prod]
        calc ∏ k ∈ Finset.Icc 1 n, |1 - (8 / 3 : ℝ) * (2 : ℝ) ^ k|
            ≤ ∏ k ∈ Finset.Icc 1 n, (8 / 3 : ℝ) * (2 : ℝ) ^ k := by
              apply Finset.prod_le_prod (fun k _ => abs_nonneg _)
              intro k hk; rw [Finset.mem_Icc] at hk
              have := two_le_pow k hk.1
              rw [abs_of_neg (by nlinarith : (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ k) < 0)]
              nlinarith
          _ = (8 / 3 : ℝ) ^ n * (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k) := by
              rw [Finset.prod_mul_distrib, Finset.prod_const, Finset.prod_pow_eq_pow_sum, Nat.card_Icc,
                Nat.add_sub_cancel]
      have hP2 : |∏ k ∈ Finset.Icc ((n + 1) / 2) n, (1 - (2 : ℝ) ^ k)| ≤ (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k) := by
        rw [Finset.abs_prod]
        calc ∏ k ∈ Finset.Icc ((n + 1) / 2) n, |1 - (2 : ℝ) ^ k|
            ≤ ∏ k ∈ Finset.Icc ((n + 1) / 2) n, (2 : ℝ) ^ k := by
              apply Finset.prod_le_prod (fun k _ => abs_nonneg _)
              intro k hk; rw [Finset.mem_Icc] at hk
              have := two_le_pow k (by omega)
              rw [abs_of_nonpos (by linarith : (1 - (2 : ℝ) ^ k) ≤ 0)]
              linarith
          _ = (2 : ℝ) ^ (∑ k ∈ Finset.Icc ((n + 1) / 2) n, k) := Finset.prod_pow_eq_pow_sum _ _ _
          _ ≤ (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k) :=
              pow_le_pow_right₀ (by norm_num)
                (Finset.sum_le_sum_of_subset (Finset.Icc_subset_Icc (by omega) (le_refl n)))
      calc (Nat.factorial (n - 2) : ℝ) * |∏ k ∈ Finset.Icc 1 n, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ k)|
            * |∏ k ∈ Finset.Icc ((n + 1) / 2) n, (1 - (2 : ℝ) ^ k)|
          ≤ (Nat.factorial (n - 2) : ℝ) * ((8 / 3 : ℝ) ^ n * (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k)) * (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k) := by
            apply mul_le_mul _ hP2 (abs_nonneg _) (mul_nonneg hfac (by positivity))
            exact mul_le_mul_of_nonneg_left hP1 hfac
        _ = _ := by ring
    have gauss_Icc : ∀ n : ℕ, 2 * (∑ k ∈ Finset.Icc 1 n, k) = n * (n + 1) := by
      intro n
      have hconv : (∑ k ∈ Finset.Icc 1 n, k) = ∑ k ∈ Finset.range (n + 1), k := by
        apply Finset.sum_subset
        · intro x hx; rw [Finset.mem_Icc] at hx; rw [Finset.mem_range]; omega
        · intro x hx hx2; rw [Finset.mem_range] at hx; rw [Finset.mem_Icc] at hx2; omega
      rw [hconv, mul_comm, Finset.sum_range_id_mul_two, Nat.add_sub_cancel, Nat.mul_comm]
    have cleared_le : ∀ n : ℕ, 1 ≤ n → |(9 : ℝ) ^ n * ((Nat.factorial (n - 2) : ℝ) * (∏ k ∈ Finset.Icc 1 n, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ k)) * (∏ k ∈ Finset.Icc ((n + 1) / 2) n, (1 - (2 : ℝ) ^ k))) * (∑' j : ℕ, (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹))|
        ≤ 2 * (Nat.factorial (n - 2) : ℝ) * (24 : ℝ) ^ n * ((2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 (n - 1), k))⁻¹ := by
      intro n hn
      have hexp : n + (∑ k ∈ Finset.Icc 1 (n - 1), k) + n ^ 2 = ((∑ k ∈ Finset.Icc 1 n, k) + (∑ k ∈ Finset.Icc 1 n, k)) + (∑ k ∈ Finset.Icc 1 (n - 1), k) := by
        have := gauss_Icc n; nlinarith
      have hq : (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k) * (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k) * ((2 : ℝ) ^ (n + (∑ k ∈ Finset.Icc 1 (n - 1), k) + n ^ 2))⁻¹ = ((2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 (n - 1), k))⁻¹ := by
        rw [← pow_add, hexp]
        nth_rewrite 2 [pow_add]
        rw [mul_inv, ← mul_assoc, mul_inv_cancel₀ (ne_of_gt (pow_pos (by norm_num) _)), one_mul]
      have hWnn : (0:ℝ) ≤ (Nat.factorial (n - 2) : ℝ) * (8 / 3 : ℝ) ^ n * (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k) * (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k) := by positivity
      rw [abs_mul, abs_mul, abs_of_nonneg (by positivity : (0 : ℝ) ≤ (9 : ℝ) ^ n)]
      calc (9 : ℝ) ^ n * |((Nat.factorial (n - 2) : ℝ) * (∏ k ∈ Finset.Icc 1 n, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ k)) * (∏ k ∈ Finset.Icc ((n + 1) / 2) n, (1 - (2 : ℝ) ^ k)))| * |(∑' j : ℕ, (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹))|
          ≤ (9 : ℝ) ^ n * ((Nat.factorial (n - 2) : ℝ) * (8 / 3 : ℝ) ^ n * (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k) * (2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 n, k))
              * (2 * ((2 : ℝ) ^ (n + (∑ k ∈ Finset.Icc 1 (n - 1), k) + n ^ 2))⁻¹) := by
            apply mul_le_mul _ (E_le n hn) (abs_nonneg _) (mul_nonneg (by positivity) hWnn)
            exact mul_le_mul_of_nonneg_left (W_le n hn) (by positivity)
        _ = 2 * (Nat.factorial (n - 2) : ℝ) * (24 : ℝ) ^ n * ((2 : ℝ) ^ (∑ k ∈ Finset.Icc 1 (n - 1), k))⁻¹ := by
            rw [← hq, show (24 : ℝ) ^ n = (9 : ℝ) ^ n * (8 / 3 : ℝ) ^ n by rw [← mul_pow]; norm_num]
            ring
    have gauss' : ∀ n : ℕ, (∑ k ∈ Finset.Icc 1 (n - 1), k) = n * (n - 1) / 2 := by
      intro n
      rcases Nat.eq_zero_or_pos n with hn0 | hn0
      · subst hn0; simp
      · have h := gauss_Icc (n - 1)
        rw [Nat.sub_add_cancel hn0, Nat.mul_comm (n - 1) n] at h
        omega
    -- The majorant (n-2)! 24^n / 2^(n(n-1)/2) tends to 0 (ratio test).
    have combine : Filter.Tendsto (fun n : ℕ => (Nat.factorial (n - 2) : ℝ) * (24 : ℝ) ^ n * ((2 : ℝ) ^ (n * (n - 1) / 2))⁻¹)
        Filter.atTop (nhds 0) := by
      have tri_succ : ∀ n : ℕ, (n + 1) * ((n + 1) - 1) / 2 = n * (n - 1) / 2 + n := by
        intro n
        have e : ∀ k : ℕ, k * (k - 1) / 2 = k.choose 2 := fun k => (Nat.choose_two_right k).symm
        rw [e, e, Nat.choose_succ_succ n 1]
        simp [Nat.choose_one_right]
        omega
      have fact_step : ∀ n : ℕ, 2 ≤ n → Nat.factorial (n - 1) = (n - 1) * Nat.factorial (n - 2) := by
        intro n hn
        obtain ⟨m, rfl⟩ : ∃ m, n = m + 2 := ⟨n - 2, by omega⟩
        simp [Nat.factorial_succ]
      have fpos : ∀ n : ℕ, 0 < (Nat.factorial (n - 2) : ℝ) * (24 : ℝ) ^ n * ((2 : ℝ) ^ (n * (n - 1) / 2))⁻¹ := by
        intro n; positivity
      have fratio : ∀ n : ℕ, 2 ≤ n →
          ((Nat.factorial ((n + 1) - 2) : ℝ) * (24 : ℝ) ^ (n + 1) * ((2 : ℝ) ^ ((n + 1) * ((n + 1) - 1) / 2))⁻¹)
            / ((Nat.factorial (n - 2) : ℝ) * (24 : ℝ) ^ n * ((2 : ℝ) ^ (n * (n - 1) / 2))⁻¹)
            = (↑(n - 1) : ℝ) * 24 * ((2 : ℝ) ^ n)⁻¹ := by
        intro n hn
        have hfn : (n + 1) - 2 = n - 1 := by omega
        rw [hfn, fact_step n hn, tri_succ n, pow_add]
        have hpos1 : (0 : ℝ) < (2 : ℝ) ^ (n * (n - 1) / 2) := by positivity
        have hpos2 : (0 : ℝ) < (2 : ℝ) ^ n := by positivity
        push_cast; field_simp; ring
      have ratio_tendsto : Filter.Tendsto (fun n : ℕ => (↑(n - 1) : ℝ) * 24 * ((2 : ℝ) ^ n)⁻¹) Filter.atTop (nhds 0) := by
        have hr : |(2 : ℝ)⁻¹| < 1 := by norm_num
        have hbase : Filter.Tendsto (fun n : ℕ => (↑n : ℝ) * ((2 : ℝ)⁻¹) ^ n) Filter.atTop (nhds 0) :=
          tendsto_self_mul_const_pow_of_abs_lt_one hr
        have hsq : Filter.Tendsto (fun n : ℕ => (↑(n - 1) : ℝ) * ((2 : ℝ)⁻¹) ^ n) Filter.atTop (nhds 0) := by
          apply squeeze_zero (fun n => by positivity) ?_ hbase
          intro n
          have hb : (0 : ℝ) ≤ ((2 : ℝ)⁻¹) ^ n := by positivity
          have hle : (↑(n - 1) : ℝ) ≤ (↑n : ℝ) := by exact_mod_cast Nat.sub_le n 1
          nlinarith [hle, hb]
        have heq : (fun n : ℕ => (↑(n - 1) : ℝ) * 24 * ((2 : ℝ) ^ n)⁻¹)
            = (fun n : ℕ => 24 * ((↑(n - 1) : ℝ) * ((2 : ℝ)⁻¹) ^ n)) := by
          funext n; rw [inv_pow]; ring
        rw [heq]; simpa using hsq.const_mul 24
      have hsummable : Summable (fun n : ℕ => (Nat.factorial (n - 2) : ℝ) * (24 : ℝ) ^ n * ((2 : ℝ) ^ (n * (n - 1) / 2))⁻¹) := by
        apply summable_of_ratio_test_tendsto_lt_one (l := 0) (by norm_num)
        · filter_upwards with n using ne_of_gt (fpos n)
        · have hcongr : (fun n : ℕ => ‖(Nat.factorial ((n + 1) - 2) : ℝ) * (24 : ℝ) ^ (n + 1) * ((2 : ℝ) ^ ((n + 1) * ((n + 1) - 1) / 2))⁻¹‖
                / ‖(Nat.factorial (n - 2) : ℝ) * (24 : ℝ) ^ n * ((2 : ℝ) ^ (n * (n - 1) / 2))⁻¹‖)
              =ᶠ[Filter.atTop] (fun n : ℕ => (↑(n - 1) : ℝ) * 24 * ((2 : ℝ) ^ n)⁻¹) := by
            filter_upwards [Filter.eventually_ge_atTop 2] with n hn
            rw [Real.norm_of_nonneg (le_of_lt (fpos _)), Real.norm_of_nonneg (le_of_lt (fpos _))]
            exact fratio n hn
          exact ratio_tendsto.congr' hcongr.symm
      exact hsummable.tendsto_atTop_zero
    have hg : Filter.Tendsto (fun n : ℕ => 2 * ((Nat.factorial (n - 2) : ℝ) * (24 : ℝ) ^ n * ((2 : ℝ) ^ (n * (n - 1) / 2))⁻¹))
        Filter.atTop (nhds 0) := by simpa using combine.const_mul 2
    refine squeeze_zero_norm' ?_ hg
    filter_upwards [Filter.eventually_ge_atTop 1] with n hn
    rw [Real.norm_eq_abs]
    refine (cleared_le n hn).trans (le_of_eq ?_)
    rw [gauss' n]
    ring
  -- Integrality, closed by the proved hole erdos-1050--h1-v2--h2. (Borwein Lemmas 1-3): b(n) z - a(n) = 9^n W(n) E(n) with integers a(n), b(n).
  have integrality : ∃ a b : ℕ → ℤ, ∀ n : ℕ, 1 ≤ n →
      (b n : ℝ) * (∑' j : ℕ, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (j + 1))⁻¹) - a n = (9 : ℝ) ^ n * ((Nat.factorial (n - 2) : ℝ) * (∏ k ∈ Finset.Icc 1 n, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ k)) * (∏ k ∈ Finset.Icc ((n + 1) / 2) n, (1 - (2 : ℝ) ^ k))) * (∑' j : ℕ, (-(1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (((n + j : ℕ) : ℤ) + n))⁻¹ * ∏ k ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ ((k : ℤ) - (n + j : ℕ))) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ ((k : ℤ) + (n + j : ℕ)))⁻¹)) :=
    erdos_1050__h1_v2__h2
  -- Assembly.
  obtain ⟨a, b, hab⟩ := integrality
  have key : ∀ n : ℕ, ((-15 * b (n + 1) : ℤ) : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - ((5 * a (n + 1) - 3 * b (n + 1) : ℤ) : ℝ) =
      5 * ((b (n + 1) : ℝ) * (∑' j : ℕ, (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ (j + 1))⁻¹) - a (n + 1)) := by
    intro n
    rw [transfer]
    push_cast
    ring
  refine ⟨fun n => 5 * a (n + 1) - 3 * b (n + 1), fun n => -15 * b (n + 1), fun n => ?_, ?_⟩
  · rw [key n, hab (n + 1) (by omega)]
    refine mul_ne_zero (by norm_num) (mul_ne_zero (mul_ne_zero (pow_ne_zero _ (by norm_num)) ?_) ?_)
    · exact w_ne (n + 1) (by omega)
    · exact e_ne (n + 1) (by omega)
  · have h5 := (decay.comp (Filter.tendsto_add_atTop_nat 1)).const_mul 5
    rw [mul_zero] at h5
    refine h5.congr (fun n => ?_)
    rw [key n, hab (n + 1) (by omega)]
    rfl
