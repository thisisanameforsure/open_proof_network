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
theorem formula3 (n k : ℕ) (hk : k ≤ n) (Qc : ℕ → ℕ → ℚ)
    (hQc : ∀ j ≤ n, Qc n j * 2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
      ∏ K ∈ Finset.Ioc n (2 * n), ((2 : ℚ) ^ j - 2 ^ K)) :
    ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1) =
      Qc n k * 2 ^ k * (∑ K ∈ Finset.Ioc n (2 * n), 1 / ((2 : ℚ) ^ k - 2 ^ K) -
        ∑ i ∈ (Finset.range (n + 1)).erase k, 1 / ((2 : ℚ) ^ k - 2 ^ i)) -
      ∑ j ∈ Finset.Ioc k n, Qc n j * 2 ^ (j - k) / (1 - 2 ^ (j - k)) := by
  set x : ℕ → ℚ := fun i => (2 : ℚ) ^ i with hxdef
  have hxinj : ∀ i ≤ n, ∀ j ≤ n, x i = x j → i = j := by
    intro i _ j _ h
    have h' : (2 : ℚ) ^ i = 2 ^ j := h
    exact Nat.pow_right_injective (le_refl 2) (by exact_mod_cast h')
  have hxne : ∀ a b : ℕ, a ≠ b → (2 : ℚ) ^ a - 2 ^ b ≠ 0 := by
    intro a b hab h
    apply hab
    exact Nat.pow_right_injective (le_refl 2) (by exact_mod_cast (sub_eq_zero.mp h))
  set S := (Finset.range (n + 1)).erase k with hS
  set T := Finset.Ioc n (2 * n) with hT
  set N : ℚ[X] := ∏ K ∈ T, (X - C ((2 : ℚ) ^ K)) with hN
  have hNdeg : N.degree ≤ n := by
    rw [hN, Polynomial.degree_prod]
    rw [Finset.sum_congr rfl (fun K _ => Polynomial.degree_X_sub_C ((2 : ℚ) ^ K)), Finset.sum_const, hT,
      Nat.card_Ioc]
    simp
    omega
  have hkmem : k ∈ Finset.range (n + 1) := Finset.mem_range.mpr (by omega)
  have hr : ∀ j ≤ n, (Qc n j * 2 ^ j) * ∏ i ∈ (Finset.range (n + 1)).erase j, (x j - x i) = N.eval (x j) := by
    intro j hj
    rw [hN, Polynomial.eval_prod]
    simp only [Polynomial.eval_sub, Polynomial.eval_X, Polynomial.eval_C, hxdef]
    exact hQc j hj
  have hD := lagr_deriv n x hxinj N hNdeg (fun j => Qc n j * 2 ^ j) hr k hk
  have hD2 : (derivative N).eval (x k) = ∑ K ∈ T, ∏ a ∈ T.erase K, (x k - 2 ^ a) := by
    rw [hN, deriv_prod_eval]
  set P := ∏ i ∈ S, (x k - x i) with hP
  have hPne : P ≠ 0 := by
    rw [hP]
    refine Finset.prod_ne_zero_iff.mpr (fun i hi => hxne k i (Ne.symm (Finset.ne_of_mem_erase hi)))
  have hNk : N.eval (x k) = (Qc n k * 2 ^ k) * P := by
    rw [← hr k hk]
  have hNk' : N.eval (x k) = ∏ K ∈ T, (x k - 2 ^ K) := by
    rw [hN, Polynomial.eval_prod]
    simp only [Polynomial.eval_sub, Polynomial.eval_X, Polynomial.eval_C]
  -- (a)
  have ha : ∀ j ∈ S, ∏ i ∈ ((Finset.range (n + 1)).erase j).erase k, (x k - x i) = P / (x k - x j) := by
    intro j hj
    have hne : x k - x j ≠ 0 := hxne k j (Ne.symm (Finset.ne_of_mem_erase hj))
    rw [Finset.erase_right_comm, eq_div_iff hne, mul_comm, hP, Finset.mul_prod_erase S (fun i => x k - x i) hj]
  have hb : ∀ l ∈ S, ∏ i ∈ S.erase l, (x k - x i) = P / (x k - x l) := by
    intro l hl
    have hne : x k - x l ≠ 0 := hxne k l (Ne.symm (Finset.ne_of_mem_erase hl))
    rw [eq_div_iff hne, mul_comm, hP, Finset.mul_prod_erase S (fun i => x k - x i) hl]
  have hc : ∀ K ∈ T, ∏ a ∈ T.erase K, (x k - 2 ^ a) = N.eval (x k) / (x k - 2 ^ K) := by
    intro K hK
    have hKn : n < K := (Finset.mem_Ioc.mp hK).1
    have hne : x k - 2 ^ K ≠ 0 := hxne k K (by omega)
    rw [eq_div_iff hne, mul_comm, hNk', Finset.mul_prod_erase T (fun a => x k - 2 ^ a) hK]
  rw [← hS] at hD
  rw [hD2, Finset.sum_congr rfl hc] at hD
  have hD3 : ∑ j ∈ S, Qc n j * 2 ^ j * ∏ i ∈ ((Finset.range (n + 1)).erase j).erase k, (x k - x i) =
      ∑ j ∈ S, Qc n j * 2 ^ j * (P / (x k - x j)) :=
    Finset.sum_congr rfl (fun j hj => by rw [ha j hj])
  have hD4 : ∑ l ∈ S, ∏ i ∈ S.erase l, (x k - x i) = ∑ l ∈ S, P / (x k - x l) :=
    Finset.sum_congr rfl hb
  rw [hD3, hD4, hNk] at hD
  -- key: sum over S of r_j / (x k - x j) = r_k * beta
  have key : ∑ j ∈ S, (Qc n j * 2 ^ j) / (x k - x j) =
      (Qc n k * 2 ^ k) * (∑ K ∈ T, 1 / (x k - 2 ^ K) - ∑ i ∈ S, 1 / (x k - x i)) := by
    have e1 : ∑ K ∈ T, Qc n k * 2 ^ k * P / (x k - 2 ^ K) = P * ((Qc n k * 2 ^ k) * ∑ K ∈ T, 1 / (x k - 2 ^ K)) := by
      rw [Finset.mul_sum, Finset.mul_sum]; refine Finset.sum_congr rfl (fun K _ => by ring)
    have e2 : ∑ j ∈ S, Qc n j * 2 ^ j * (P / (x k - x j)) = P * ∑ j ∈ S, (Qc n j * 2 ^ j) / (x k - x j) := by
      rw [Finset.mul_sum]; refine Finset.sum_congr rfl (fun j _ => by ring)
    have e3 : ∑ l ∈ S, P / (x k - x l) = P * ∑ i ∈ S, 1 / (x k - x i) := by
      rw [Finset.mul_sum]; refine Finset.sum_congr rfl (fun j _ => by ring)
    rw [e1, e2, e3] at hD
    apply mul_left_cancel₀ hPne
    linear_combination -hD
  -- split S into range k and Ioc k n
  have hsplit : S = Finset.range k ∪ Finset.Ioc k n := by
    rw [hS]; ext x; simp only [Finset.mem_erase, Finset.mem_range, Finset.mem_union, Finset.mem_Ioc]; omega
  have hdisj : Disjoint (Finset.range k) (Finset.Ioc k n) := by
    rw [Finset.disjoint_left]; intro a ha ha'
    simp only [Finset.mem_range, Finset.mem_Ioc] at ha ha'; omega
  rw [hsplit, Finset.sum_union hdisj] at key
  have hlow : ∀ j ∈ Finset.range k, (Qc n j * 2 ^ j) / (x k - x j) = Qc n j / ((2 : ℚ) ^ (k - j) - 1) := by
    intro j hj
    have hjk : j < k := Finset.mem_range.mp hj
    have hne : (2 : ℚ) ^ (k - j) - 1 ≠ 0 := by
      have : (1 : ℚ) < 2 ^ (k - j) := one_lt_pow₀ (by norm_num) (by omega)
      linarith
    have hne2 : (2 : ℚ) ^ k - 2 ^ j ≠ 0 := hxne k j (by omega)
    simp only [hxdef]
    rw [div_eq_div_iff hne2 hne, show k = j + (k - j) by omega, pow_add]
    simp only [show j + (k - j) - j = k - j by omega]
    ring
  have hhigh : ∀ j ∈ Finset.Ioc k n, (Qc n j * 2 ^ j) / (x k - x j) = Qc n j * 2 ^ (j - k) / (1 - 2 ^ (j - k)) := by
    intro j hj
    have hkj : k < j := (Finset.mem_Ioc.mp hj).1
    have hne : (1 : ℚ) - 2 ^ (j - k) ≠ 0 := by
      have : (1 : ℚ) < 2 ^ (j - k) := one_lt_pow₀ (by norm_num) (by omega)
      linarith
    have hne2 : (2 : ℚ) ^ k - 2 ^ j ≠ 0 := hxne k j (by omega)
    simp only [hxdef]
    rw [div_eq_div_iff hne2 hne, show j = k + (j - k) by omega, pow_add]
    simp only [show k + (j - k) - k = j - k by omega]
    ring
  rw [Finset.sum_congr rfl hlow, Finset.sum_congr rfl hhigh] at key
  rw [Finset.sum_range_succ, Nat.sub_self, pow_zero, sub_self, div_zero, add_zero]
  simp only [hxdef] at key
  rw [← hsplit] at key
  linear_combination key
