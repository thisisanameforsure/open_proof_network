import Mathlib

open Polynomial in
theorem lagr_eval (n : ℕ) (x : ℕ → ℚ) (hx : ∀ i ≤ n, ∀ j ≤ n, x i = x j → i = j)
    (N : ℚ[X]) (hNdeg : N.degree ≤ n) (r : ℕ → ℚ)
    (hr : ∀ j ≤ n, r j * ∏ i ∈ (Finset.range (n + 1)).erase j, (x j - x i) = N.eval (x j)) :
    N = ∑ j ∈ Finset.range (n + 1), C (r j) * ∏ i ∈ (Finset.range (n + 1)).erase j, (X - C (x i)) := by
  have hinj : Set.InjOn x (Finset.range (n + 1) : Set ℕ) := by
    intro i hi j hj h
    simp only [Finset.coe_range, Set.mem_Iio] at hi hj
    exact hx i (by omega) j (by omega) h
  apply Polynomial.eq_of_degree_sub_lt_of_eval_finset_eq ((Finset.range (n + 1)).image x)
  · rw [Finset.card_image_of_injOn hinj, Finset.card_range]
    refine lt_of_le_of_lt (Polynomial.degree_sub_le _ _) (max_lt ?_ ?_)
    · exact lt_of_le_of_lt hNdeg (by exact_mod_cast Nat.lt_succ_self n)
    · refine lt_of_le_of_lt (Polynomial.degree_sum_le _ _) ?_
      rw [Finset.sup_lt_iff (by exact WithBot.bot_lt_coe _)]
      intro j hj
      refine lt_of_le_of_lt (Polynomial.degree_mul_le _ _) ?_
      refine lt_of_le_of_lt (add_le_add (Polynomial.degree_C_le) (Polynomial.degree_prod_le _ _)) ?_
      have : ∑ i ∈ (Finset.range (n + 1)).erase j, (X - C (x i)).degree = ((n : ℕ) : WithBot ℕ) := by
        rw [Finset.sum_congr rfl (fun i _ => Polynomial.degree_X_sub_C (x i)), Finset.sum_const,
          Finset.card_erase_of_mem hj, Finset.card_range, Nat.add_sub_cancel]
        simp
      rw [this, zero_add]
      exact_mod_cast Nat.lt_succ_self n
  · intro y hy
    obtain ⟨k, hk, rfl⟩ := Finset.mem_image.mp hy
    have hk' : k ≤ n := by have := Finset.mem_range.mp hk; omega
    rw [← hr k hk', Polynomial.eval_finset_sum, Finset.sum_eq_single k]
    · simp [Polynomial.eval_prod]
    · intro j hj hjk
      simp only [Polynomial.eval_mul, Polynomial.eval_C, Polynomial.eval_prod, Polynomial.eval_sub,
        Polynomial.eval_X]
      rw [Finset.prod_eq_zero (i := k) (Finset.mem_erase.mpr ⟨Ne.symm hjk, hk⟩) (by ring), mul_zero]
    · intro h; exact absurd hk h

open Polynomial in
theorem deriv_prod_eval (S : Finset ℕ) (x : ℕ → ℚ) (z : ℚ) :
    (derivative (∏ i ∈ S, (X - C (x i)))).eval z = ∑ l ∈ S, ∏ i ∈ S.erase l, (z - x i) := by
  rw [Polynomial.derivative_prod_finset, Polynomial.eval_finset_sum]
  refine Finset.sum_congr rfl (fun l _ => ?_)
  simp [Polynomial.eval_prod]

open Polynomial in
theorem deriv_prod_eval_node (S : Finset ℕ) (x : ℕ → ℚ) (k : ℕ) (hk : k ∈ S) :
    (derivative (∏ i ∈ S, (X - C (x i)))).eval (x k) = ∏ i ∈ S.erase k, (x k - x i) := by
  rw [deriv_prod_eval, Finset.sum_eq_single k]
  · intro l hl hlk
    exact Finset.prod_eq_zero (i := k) (Finset.mem_erase.mpr ⟨Ne.symm hlk, hk⟩) (by ring)
  · intro h; exact absurd hk h

open Polynomial in
theorem lagr_deriv (n : ℕ) (x : ℕ → ℚ) (hx : ∀ i ≤ n, ∀ j ≤ n, x i = x j → i = j)
    (N : ℚ[X]) (hNdeg : N.degree ≤ n) (r : ℕ → ℚ)
    (hr : ∀ j ≤ n, r j * ∏ i ∈ (Finset.range (n + 1)).erase j, (x j - x i) = N.eval (x j))
    (k : ℕ) (hk : k ≤ n) :
    (derivative N).eval (x k) =
      ∑ j ∈ (Finset.range (n + 1)).erase k, r j * ∏ i ∈ ((Finset.range (n + 1)).erase j).erase k, (x k - x i) +
      r k * ∑ l ∈ (Finset.range (n + 1)).erase k, ∏ i ∈ ((Finset.range (n + 1)).erase k).erase l, (x k - x i) := by
  have hkmem : k ∈ Finset.range (n + 1) := Finset.mem_range.mpr (by omega)
  conv_lhs => rw [lagr_eval n x hx N hNdeg r hr]
  rw [Polynomial.derivative_sum, Polynomial.eval_finset_sum, ← Finset.add_sum_erase _ _ hkmem, add_comm]
  congr 1
  · refine Finset.sum_congr rfl (fun j hj => ?_)
    have hjk : j ≠ k := Finset.ne_of_mem_erase hj
    rw [Polynomial.derivative_C_mul, Polynomial.eval_mul, Polynomial.eval_C,
      deriv_prod_eval_node _ x k (Finset.mem_erase.mpr ⟨Ne.symm hjk, hkmem⟩)]
  · rw [Polynomial.derivative_C_mul, Polynomial.eval_mul, Polynomial.eval_C, deriv_prod_eval]

open Polynomial in
theorem tail_coeff (n K : ℕ) (hK : n < K) (Qc : ℕ → ℕ → ℚ)
    (hQc : ∀ j ≤ n, Qc n j * 2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
      ∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℚ) ^ j - 2 ^ L)) :
    ∑ j ∈ Finset.range (n + 1), Qc n j / ((2 : ℚ) ^ (K - j) - 1) =
      (∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℚ) ^ K - 2 ^ L)) / ∏ i ∈ Finset.range (n + 1), ((2 : ℚ) ^ K - 2 ^ i) := by
  set x : ℕ → ℚ := fun i => (2 : ℚ) ^ i with hxdef
  have hxinj : ∀ i ≤ n, ∀ j ≤ n, x i = x j → i = j := by
    intro i _ j _ h
    have h' : (2 : ℚ) ^ i = 2 ^ j := h
    exact Nat.pow_right_injective (le_refl 2) (by exact_mod_cast h')
  have hxne : ∀ a b : ℕ, a ≠ b → (2 : ℚ) ^ a - 2 ^ b ≠ 0 := by
    intro a b hab h
    apply hab
    exact Nat.pow_right_injective (le_refl 2) (by exact_mod_cast (sub_eq_zero.mp h))
  set N : ℚ[X] := ∏ L ∈ Finset.Ioc n (2 * n), (X - C ((2 : ℚ) ^ L)) with hN
  have hNdeg : N.degree ≤ n := by
    rw [hN, Polynomial.degree_prod]
    rw [Finset.sum_congr rfl (fun L _ => Polynomial.degree_X_sub_C ((2 : ℚ) ^ L)), Finset.sum_const,
      Nat.card_Ioc]
    simp
    omega
  have hr : ∀ j ≤ n, (Qc n j * 2 ^ j) * ∏ i ∈ (Finset.range (n + 1)).erase j, (x j - x i) = N.eval (x j) := by
    intro j hj
    rw [hN, Polynomial.eval_prod]
    simp only [Polynomial.eval_sub, Polynomial.eval_X, Polynomial.eval_C, hxdef]
    exact hQc j hj
  have hL := lagr_eval n x hxinj N hNdeg (fun j => Qc n j * 2 ^ j) hr
  have hev := congrArg (Polynomial.eval ((2 : ℚ) ^ K)) hL
  rw [Polynomial.eval_finset_sum] at hev
  have hNK : N.eval ((2 : ℚ) ^ K) = ∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℚ) ^ K - 2 ^ L) := by
    rw [hN, Polynomial.eval_prod]
    simp only [Polynomial.eval_sub, Polynomial.eval_X, Polynomial.eval_C]
  have hD : ∏ i ∈ Finset.range (n + 1), ((2 : ℚ) ^ K - 2 ^ i) ≠ 0 :=
    Finset.prod_ne_zero_iff.mpr (fun i hi => hxne K i (by have := Finset.mem_range.mp hi; omega))
  rw [hNK] at hev
  rw [hev, Finset.sum_div]
  refine Finset.sum_congr rfl (fun j hj => ?_)
  have hjn : j < n + 1 := Finset.mem_range.mp hj
  have hne1 : (2 : ℚ) ^ K - 2 ^ j ≠ 0 := hxne K j (by omega)
  have hne2 : (2 : ℚ) ^ (K - j) - 1 ≠ 0 := by
    have : (1 : ℚ) < 2 ^ (K - j) := one_lt_pow₀ (by norm_num) (by omega)
    linarith
  simp only [Polynomial.eval_mul, Polynomial.eval_C, Polynomial.eval_prod, Polynomial.eval_sub,
    Polynomial.eval_X, hxdef]
  rw [← Finset.mul_prod_erase (Finset.range (n + 1)) (fun i => (2 : ℚ) ^ K - 2 ^ i) hj]
  have hE : ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ K - 2 ^ i) ≠ 0 :=
    Finset.prod_ne_zero_iff.mpr (fun i hi => hxne K i (by
      have := Finset.mem_range.mp (Finset.mem_of_mem_erase hi); omega))
  have hpow : (2 : ℚ) ^ K = 2 ^ j * 2 ^ (K - j) := by rw [← pow_add]; congr 1; omega
  field_simp
  rw [hpow]
  ring
