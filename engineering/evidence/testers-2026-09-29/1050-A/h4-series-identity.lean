import Mathlib

theorem id1_test (n j : ℕ) (hj : j ≤ n) :
    (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1)) * ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) =
      ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1) := by
  induction j with
  | zero => simp
  | succ j ih =>
    have ih' := ih (by omega)
    rw [Finset.prod_range_succ, ← ih']
    obtain ⟨m, hm⟩ : ∃ m, n - j = m + 1 := ⟨n - j - 1, by omega⟩
    rw [hm, Finset.prod_range_succ, show n - (j + 1) = m by omega]
    ring

theorem lower_test (j : ℕ) :
    ∏ i ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ i) =
      2 ^ (j * (j - 1) / 2) * ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1) := by
  have h1 : ∀ i ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ i) = 2 ^ i * (2 ^ (j - 1 - i + 1) - 1) := by
    intro i hi
    have hi' := Finset.mem_range.mp hi
    rw [mul_sub, ← pow_add, show i + (j - 1 - i + 1) = j by omega]
    ring
  rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_pow_eq_pow_sum,
    Finset.prod_range_reflect (fun s => ((2 : ℚ) ^ (s + 1) - 1)) j]
  congr 1
  congr 1
  have := Finset.sum_range_id_mul_two j
  omega

theorem upper_test (j n : ℕ) (hj : j ≤ n) :
    ∏ i ∈ Finset.Ioc j n, ((2 : ℚ) ^ j - 2 ^ i) =
      (-1) ^ (n - j) * 2 ^ (j * (n - j)) * ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) := by
  have e : Finset.Ioc j n = Finset.Ico (j + 1) (n + 1) := by
    ext x; simp only [Finset.mem_Ioc, Finset.mem_Ico]; omega
  rw [e, Finset.prod_Ico_eq_prod_range, show n + 1 - (j + 1) = n - j by omega]
  have h1 : ∀ t ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + t)) = (-1) * 2 ^ j * (2 ^ (t + 1) - 1) := by
    intro t _
    rw [show j + 1 + t = j + (t + 1) by ring, pow_add]
    ring
  rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_mul_distrib, Finset.prod_const,
    Finset.prod_const, Finset.card_range, ← pow_mul]

theorem rhs_test (j n : ℕ) (hj : j ≤ n) :
    (∏ K ∈ Finset.Ioc n (2 * n), ((2 : ℚ) ^ j - 2 ^ K)) *
      ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) =
      (-1) ^ n * 2 ^ (j * n) * ∏ s ∈ Finset.range (2 * n - j), ((2 : ℚ) ^ (s + 1) - 1) := by
  have e : Finset.Ioc n (2 * n) = Finset.Ico (n + 1) (2 * n + 1) := by
    ext x; simp only [Finset.mem_Ioc, Finset.mem_Ico]; omega
  rw [e, Finset.prod_Ico_eq_prod_range, show 2 * n + 1 - (n + 1) = n by omega]
  have h1 : ∀ t ∈ Finset.range n, ((2 : ℚ) ^ j - 2 ^ (n + 1 + t)) =
      (-1) * 2 ^ j * (2 ^ ((n - j) + t + 1) - 1) := by
    intro t _
    rw [show n + 1 + t = j + ((n - j) + t + 1) by omega, pow_add]
    ring
  rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_mul_distrib, Finset.prod_const,
    Finset.prod_const, Finset.card_range, ← pow_mul,
    show 2 * n - j = (n - j) + n by omega, Finset.prod_range_add]
  ring

theorem id1_full (n j : ℕ) (hj : j ≤ n) :
    (((-1 : ℚ) ^ j * (2 : ℚ) ^ (j * (j - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - j - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
      2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
    ∏ K ∈ Finset.Ioc n (2 * n), ((2 : ℚ) ^ j - 2 ^ K) := by
  have hPne : ∀ m : ℕ, ∏ s ∈ Finset.range m, ((2 : ℚ) ^ (s + 1) - 1) ≠ 0 := by
    intro m
    refine Finset.prod_ne_zero_iff.mpr (fun s _ => ?_)
    have : (1 : ℚ) < 2 ^ (s + 1) := one_lt_pow₀ (by norm_num) (by omega)
    linarith
  have hG1 : ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ)) =
      (∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1)) /
        ((∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1)) * ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1)) := by
    rw [Finset.prod_div_distrib, ← id1_test n j hj]
    field_simp [hPne]
  have hG2 : ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - j - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ)) =
      (∏ s ∈ Finset.range (2 * n - j), ((2 : ℚ) ^ (s + 1) - 1)) /
        ((∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1)) * ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1)) := by
    rw [Finset.prod_div_distrib, ← id1_test (2 * n - j) n (by omega), show 2 * n - j - n = n - j by omega]
    field_simp [hPne]
  have hsplit : (Finset.range (n + 1)).erase j = Finset.range j ∪ Finset.Ioc j n := by
    ext x; simp only [Finset.mem_erase, Finset.mem_range, Finset.mem_union, Finset.mem_Ioc]; omega
  have hdisj : Disjoint (Finset.range j) (Finset.Ioc j n) := by
    rw [Finset.disjoint_left]
    intro x hx hx'
    simp only [Finset.mem_range, Finset.mem_Ioc] at hx hx'
    omega
  have hR := rhs_test j n hj
  obtain ⟨m, rfl⟩ := Nat.exists_eq_add_of_le hj
  have hsign : (-1 : ℚ) ^ (j + m) = (-1) ^ j * (-1) ^ (j + m - j) := by
    rw [← pow_add]; congr 1; omega
  have ha : 2 * (j * (j - 1) / 2) = j * (j - 1) := Nat.two_mul_div_two_of_even (Nat.even_mul_pred_self _)
  have hexp : j * (j + m) = j * (j - (1 : ℕ)) / (2 : ℕ) + j + j * (j - (1 : ℕ)) / (2 : ℕ) + j * (j + m - j) := by
    rw [show j + m - j = m by omega]
    rcases j with _ | i
    · simp
    · simp only [Nat.add_sub_cancel] at ha ⊢
      nlinarith [ha]
  rw [hG1, hG2, hsplit, Finset.prod_union hdisj, lower_test, upper_test j (j + m) hj]
  apply mul_right_cancel₀ (hPne (j + m - j))
  rw [hR, hsign, hexp, pow_add, pow_add, pow_add]
  field_simp [hPne]


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


theorem tail3 (n : ℕ) (hn : 1 ≤ n) :
    ∑' m : ℕ, (3 : ℝ) / (2 ^ (m + n + 1) - 3) = ∑' s : ℕ, ((3 : ℝ) / 2 ^ n) ^ (s + 1) / (2 ^ (s + 1) - 1) := by
  set f : ℕ → ℕ → ℝ := fun m s => ((3 : ℝ) / 2 ^ (n + 1)) ^ (s + 1) * ((1 : ℝ) / 2 ^ (s + 1)) ^ m with hf
  have key : ∀ m s, f m s = ((3 : ℝ) / 2 ^ (m + n + 1)) ^ (s + 1) := by
    intro m s
    simp only [hf]
    rw [div_pow, div_pow, div_pow, one_pow, ← pow_mul, ← pow_mul, ← pow_mul,
      show (m + n + 1) * (s + 1) = (n + 1) * (s + 1) + (s + 1) * m by ring, pow_add]
    field_simp
    exact pow_add _ _ _
  have hpos : ∀ m s, 0 ≤ f m s := fun m s => by rw [key]; positivity
  have h4 : ∀ m : ℕ, (4 : ℝ) ≤ 2 ^ (m + n + 1) := by
    intro m
    calc (4 : ℝ) = 2 ^ 2 := by norm_num
      _ ≤ 2 ^ (m + n + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
  have inner1 : ∀ m, HasSum (f m) ((3 : ℝ) / (2 ^ (m + n + 1) - 3)) := by
    intro m
    have hr0 : 0 ≤ (3 : ℝ) / 2 ^ (m + n + 1) := by positivity
    have hr1 : (3 : ℝ) / 2 ^ (m + n + 1) < 1 := by
      rw [div_lt_one (by positivity)]; linarith [h4 m]
    have hg := (hasSum_geometric_of_lt_one hr0 hr1).mul_left ((3 : ℝ) / 2 ^ (m + n + 1))
    have hfun : f m = fun s => (3 : ℝ) / 2 ^ (m + n + 1) * ((3 : ℝ) / 2 ^ (m + n + 1)) ^ s := by
      funext s; rw [key]; ring
    have hne : (2 : ℝ) ^ (m + n + 1) - 3 ≠ 0 := by linarith [h4 m]
    have hne2 : (2 : ℝ) ^ (m + n + 1) ≠ 0 := by positivity
    have hval : (3 : ℝ) / (2 ^ (m + n + 1) - 3) =
        3 / 2 ^ (m + n + 1) * (1 - 3 / 2 ^ (m + n + 1))⁻¹ := by
      field_simp
    rw [hfun, hval]
    exact hg
  have inner2 : ∀ s, HasSum (fun m => f m s) (((3 : ℝ) / 2 ^ n) ^ (s + 1) / (2 ^ (s + 1) - 1)) := by
    intro s
    have hr0 : 0 ≤ (1 : ℝ) / 2 ^ (s + 1) := by positivity
    have hr1 : (1 : ℝ) / 2 ^ (s + 1) < 1 := by
      rw [div_lt_one (by positivity)]
      exact one_lt_pow₀ (by norm_num) (by omega)
    have hg := (hasSum_geometric_of_lt_one hr0 hr1).mul_left (((3 : ℝ) / 2 ^ (n + 1)) ^ (s + 1))
    have hne : (2 : ℝ) ^ (s + 1) - 1 ≠ 0 := by
      have : (1 : ℝ) < 2 ^ (s + 1) := one_lt_pow₀ (by norm_num) (by omega)
      linarith
    have hval : ((3 : ℝ) / 2 ^ n) ^ (s + 1) / (2 ^ (s + 1) - 1) =
        ((3 : ℝ) / 2 ^ (n + 1)) ^ (s + 1) * (1 - 1 / 2 ^ (s + 1))⁻¹ := by
      rw [div_pow, div_pow, ← pow_mul, ← pow_mul, show (n + 1) * (s + 1) = n * (s + 1) + (s + 1) by ring, pow_add]
      field_simp
      exact pow_add _ _ _
    rw [hval]
    exact hg
  have hsum1 : Summable (fun m : ℕ => (3 : ℝ) / (2 ^ (m + n + 1) - 3)) := by
    refine Summable.of_nonneg_of_le (fun m => ?_) (fun m => ?_) ((summable_geometric_two).mul_left 3)
    · have := h4 m; exact div_nonneg (by norm_num) (by linarith)
    · have hpow : (2 : ℝ) ^ (m + 2) ≤ 2 ^ (m + n + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
      have h1 : (1 : ℝ) ≤ 2 ^ m := one_le_pow₀ (by norm_num)
      have h2 : (2 : ℝ) ^ (m + 2) = 4 * 2 ^ m := by rw [pow_add]; ring
      calc (3 : ℝ) / (2 ^ (m + n + 1) - 3) ≤ 3 / 2 ^ m :=
            div_le_div_of_nonneg_left (by norm_num) (by positivity) (by linarith)
        _ = 3 * (1 / 2) ^ m := by rw [one_div_pow]; ring
  have hU : Summable (Function.uncurry f) := by
    refine (summable_prod_of_nonneg (fun p => hpos p.1 p.2)).mpr ⟨fun m => (inner1 m).summable, ?_⟩
    exact hsum1.congr (fun m => ((inner1 m).tsum_eq).symm)
  have hcomm := hU.tsum_comm' (fun m => (inner1 m).summable) (fun s => (inner2 s).summable)
  rw [show (∑' m : ℕ, (3 : ℝ) / (2 ^ (m + n + 1) - 3)) = ∑' m, ∑' s, f m s from
    tsum_congr (fun m => ((inner1 m).tsum_eq).symm)]
  rw [← hcomm]
  exact tsum_congr (fun s => (inner2 s).tsum_eq)


theorem split3T (n : ℕ) :
    3 * ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) =
      ∑ j ∈ Finset.range n, (3 : ℝ) / (2 ^ (j + 1) - 3) + ∑' m : ℕ, (3 : ℝ) / (2 ^ (m + n + 1) - 3) := by
  set g : ℕ → ℝ := fun m => (3 : ℝ) / (2 ^ (m + 1) - 3) with hg
  have hsum : Summable (fun m => g (m + 1)) := by
    refine Summable.of_nonneg_of_le (fun m => ?_) (fun m => ?_) ((summable_geometric_two).mul_left 3)
    · have : (4 : ℝ) ≤ 2 ^ (m + 1 + 1) := by
        calc (4 : ℝ) = 2 ^ 2 := by norm_num
          _ ≤ 2 ^ (m + 1 + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
      simp only [hg]; exact div_nonneg (by norm_num) (by linarith)
    · have hpow : (2 : ℝ) ^ (m + 2) ≤ 2 ^ (m + 1 + 1) := le_of_eq (by ring_nf)
      have h1 : (1 : ℝ) ≤ 2 ^ m := one_le_pow₀ (by norm_num)
      have h2 : (2 : ℝ) ^ (m + 2) = 4 * 2 ^ m := by rw [pow_add]; ring
      simp only [hg]
      calc (3 : ℝ) / (2 ^ (m + 1 + 1) - 3) ≤ 3 / 2 ^ m :=
            div_le_div_of_nonneg_left (by norm_num) (by positivity) (by linarith)
        _ = 3 * (1 / 2) ^ m := by rw [one_div_pow]; ring
  have hs : Summable g := (summable_nat_add_iff 1).mp hsum
  have e1 := hs.sum_add_tsum_nat_add n
  have e2 := hs.sum_add_tsum_nat_add 2
  have h3T : 3 * ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) = ∑' m, g (m + 2) := by
    rw [← tsum_mul_left]
    refine tsum_congr (fun m => ?_)
    simp only [hg]
    rw [show m + 2 + 1 = m + 3 by ring]
    ring
  have hfirst : ∑ i ∈ Finset.range 2, g i = 0 := by
    simp only [hg, Finset.sum_range_succ, Finset.sum_range_zero]
    norm_num
  rw [h3T]
  have htail : ∑' m : ℕ, (3 : ℝ) / (2 ^ (m + n + 1) - 3) = ∑' m, g (m + n) := by
    refine tsum_congr (fun m => ?_)
    simp only [hg]
  rw [htail]
  have hrange : ∑ j ∈ Finset.range n, (3 : ℝ) / (2 ^ (j + 1) - 3) = ∑ i ∈ Finset.range n, g i := by
    simp only [hg]
  rw [hrange, e1]
  rw [← e2, hfirst, zero_add]


theorem cauchy_fin (n : ℕ) (q a : ℕ → ℝ) (x A : ℝ) (hA : HasSum (fun s => a s * x ^ (s + 1)) A) :
    HasSum (fun K => ∑ j ∈ Finset.range (n + 1), if j < K then q j * a (K - j - 1) * x ^ K else 0)
      ((∑ j ∈ Finset.range (n + 1), q j * x ^ j) * A) := by
  rw [Finset.sum_mul]
  apply hasSum_sum
  intro j _
  have h := hA.mul_left (q j * x ^ j)
  rw [← hasSum_nat_add_iff' (j + 1)]
  have hz : ∑ i ∈ Finset.range (j + 1), (if j < i then q j * a (i - j - 1) * x ^ i else 0) = 0 :=
    Finset.sum_eq_zero (fun i hi => by
      have := Finset.mem_range.mp hi
      rw [if_neg (by omega)])
  rw [hz, sub_zero]
  have hfun : (fun s => if j < s + (j + 1) then q j * a (s + (j + 1) - j - 1) * x ^ (s + (j + 1)) else 0) =
      fun s => q j * x ^ j * (a s * x ^ (s + 1)) := by
    funext s
    rw [if_pos (by omega), show s + (j + 1) - j - 1 = s by omega, show s + (j + 1) = j + (s + 1) by ring, pow_add]
    ring
  rw [hfun]
  exact h

theorem h4_series (Qc : ℕ → ℕ → ℚ) (hQc : (Qc = fun (n k : ℕ) =>
      ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
          ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ)))) (Qx : ℕ → ℚ) (hQx : (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k))
    (Aq : ℕ → ℚ) (hAq : (Aq = fun (n : ℕ) =>
              ∑ k ∈ Finset.range (n + (1 : ℕ)),
                  (∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) *
                    ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
                Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ)))) (n : ℕ) (hn : 1 ≤ n) :
    HasSum (fun K : ℕ => if 2 * n < K then
        ((∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L)) / ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i)) *
          ((3 : ℝ) / 2 ^ n) ^ K else 0)
      ((Qx n : ℝ) * (3 * ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3)) - (Aq n : ℝ)) := by
  set x : ℝ := (3 : ℝ) / 2 ^ n with hxdef
  have hx0 : 0 ≤ x := by positivity
  have hx2 : x / 2 < 1 := by
    have : (2 : ℝ) ≤ 2 ^ n := by
      calc (2 : ℝ) = 2 ^ 1 := by norm_num
        _ ≤ 2 ^ n := pow_le_pow_right₀ (by norm_num) hn
    rw [hxdef, div_div, div_lt_one (by positivity)]; linarith
  set a : ℕ → ℝ := fun s => (1 : ℝ) / (2 ^ (s + 1) - 1) with hadef
  have hapos : ∀ s, 0 < (2 : ℝ) ^ (s + 1) - 1 := fun s => by
    have : (1 : ℝ) < 2 ^ (s + 1) := one_lt_pow₀ (by norm_num) (by omega)
    linarith
  have hAsum : Summable (fun s => a s * x ^ (s + 1)) := by
    refine Summable.of_nonneg_of_le (fun s => ?_) (fun s => ?_) ((summable_geometric_of_lt_one (by positivity) hx2).mul_left x)
    · simp only [hadef]; exact mul_nonneg (div_nonneg (by norm_num) (le_of_lt (hapos s))) (by positivity)
    · simp only [hadef]
      have h1 : (2 : ℝ) ^ s ≤ 2 ^ (s + 1) - 1 := by
        have : (1 : ℝ) ≤ 2 ^ s := one_le_pow₀ (by norm_num)
        rw [pow_succ]; linarith
      have hxs : 0 ≤ x ^ (s + 1) := by positivity
      calc 1 / (2 ^ (s + 1) - 1) * x ^ (s + 1) ≤ 1 / 2 ^ s * x ^ (s + 1) := by
            gcongr
        _ = x * (x / 2) ^ s := by
          have e : ∀ y : ℝ, 1 / 2 ^ s * y ^ (s + 1) = y * (y / 2) ^ s := by
            intro y; rw [div_pow, pow_succ]; field_simp
          exact e x
  set A := ∑' s, a s * x ^ (s + 1) with hAdef
  have hA : HasSum (fun s => a s * x ^ (s + 1)) A := hAsum.hasSum
  -- 3T = c + A
  have h3T : 3 * ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) = ∑ j ∈ Finset.range n, (3 : ℝ) / (2 ^ (j + 1) - 3) + A := by
    rw [split3T n, tail3 n hn, hAdef]
    congr 1
    refine tsum_congr (fun s => ?_)
    simp only [hadef, hxdef]
    ring
  have hQxR : (Qx n : ℝ) = ∑ j ∈ Finset.range (n + 1), (Qc n j : ℝ) * x ^ j := by
    rw [hQx]; push_cast; rfl
  have hAqR : (Aq n : ℝ) = ∑ k ∈ Finset.range (n + 1),
      (∑ j ∈ Finset.range (k + 1), (Qc n j : ℝ) / ((2 : ℝ) ^ (k - j) - 1)) * x ^ k +
      (Qx n : ℝ) * ∑ j ∈ Finset.range n, (3 : ℝ) / (2 ^ (j + 1) - 3) := by
    rw [hAq]; push_cast; rfl
  have hC := cauchy_fin n (fun j => (Qc n j : ℝ)) a x A hA
  set P : ℝ := ∑ k ∈ Finset.range (n + 1),
      (∑ j ∈ Finset.range (k + 1), (Qc n j : ℝ) / ((2 : ℝ) ^ (k - j) - 1)) * x ^ k with hPdef
  have hP : HasSum (fun K => if K < n + 1 then
      (∑ j ∈ Finset.range (K + 1), (Qc n j : ℝ) / ((2 : ℝ) ^ (K - j) - 1)) * x ^ K else 0) P := by
    have h0 : HasSum (fun K => if K < n + 1 then
        (∑ j ∈ Finset.range (K + 1), (Qc n j : ℝ) / ((2 : ℝ) ^ (K - j) - 1)) * x ^ K else 0)
        (∑ K ∈ Finset.range (n + 1), if K < n + 1 then
          (∑ j ∈ Finset.range (K + 1), (Qc n j : ℝ) / ((2 : ℝ) ^ (K - j) - 1)) * x ^ K else 0) :=
      hasSum_sum_of_ne_finset_zero (fun b hb => by rw [if_neg (by simpa using hb)])
    have h1 : (∑ K ∈ Finset.range (n + 1), if K < n + 1 then
          (∑ j ∈ Finset.range (K + 1), (Qc n j : ℝ) / ((2 : ℝ) ^ (K - j) - 1)) * x ^ K else 0) = P := by
      rw [hPdef]
      exact Finset.sum_congr rfl (fun K hK => by rw [if_pos (Finset.mem_range.mp hK)])
    rw [h1] at h0
    exact h0
  have hD := hC.sub hP
  have hval : (Qx n : ℝ) * (3 * ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3)) - (Aq n : ℝ) =
      (∑ j ∈ Finset.range (n + 1), (Qc n j : ℝ) * x ^ j) * A - P := by
    rw [h3T, hAqR, hQxR]; ring
  rw [hval]
  have hid1 : ∀ j ≤ n, Qc n j * 2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
      ∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℚ) ^ j - 2 ^ L) := fun j hj => by subst hQc; exact id1_full n j hj
  have hfun : (fun K : ℕ => if 2 * n < K then
        ((∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L)) / ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i)) *
          ((3 : ℝ) / 2 ^ n) ^ K else 0) =
      fun K => (∑ j ∈ Finset.range (n + 1), if j < K then (Qc n j : ℝ) * a (K - j - 1) * x ^ K else 0) -
        (if K < n + 1 then (∑ j ∈ Finset.range (K + 1), (Qc n j : ℝ) / ((2 : ℝ) ^ (K - j) - 1)) * x ^ K else 0) := by
    funext K
    symm
    by_cases hK : K < n + 1
    · rw [if_pos hK, if_neg (by omega)]
      rw [Finset.sum_range_succ (fun j => (Qc n j : ℝ) / ((2 : ℝ) ^ (K - j) - 1)) K, Nat.sub_self, pow_zero, sub_self,
        div_zero, add_zero]
      have hsplit : ∑ j ∈ Finset.range (n + 1), (if j < K then (Qc n j : ℝ) * a (K - j - 1) * x ^ K else 0) =
          ∑ j ∈ Finset.range K, (Qc n j : ℝ) / ((2 : ℝ) ^ (K - j) - 1) * x ^ K := by
        rw [← Finset.sum_range_add_sum_Ico _ (show K ≤ n + 1 by omega)]
        rw [Finset.sum_eq_zero (s := Finset.Ico K (n + 1)) (fun j hj => by
          rw [if_neg (by have := Finset.mem_Ico.mp hj; omega)]), add_zero]
        refine Finset.sum_congr rfl (fun j hj => ?_)
        have hjK := Finset.mem_range.mp hj
        rw [if_pos hjK]
        simp only [hadef]
        rw [show K - j - 1 + 1 = K - j by omega]
        ring
      rw [hsplit, Finset.sum_mul, sub_self]
    · rw [if_neg hK, sub_zero]
      have hS : ∑ j ∈ Finset.range (n + 1), (if j < K then (Qc n j : ℝ) * a (K - j - 1) * x ^ K else 0) =
          ((∑ j ∈ Finset.range (n + 1), Qc n j / ((2 : ℚ) ^ (K - j) - 1) : ℚ) : ℝ) * x ^ K := by
        push_cast
        rw [Finset.sum_mul]
        refine Finset.sum_congr rfl (fun j hj => ?_)
        have hjK : j < K := by have := Finset.mem_range.mp hj; omega
        rw [if_pos hjK]
        simp only [hadef]
        rw [show K - j - 1 + 1 = K - j by omega]
        ring
      rw [hS, tail_coeff n K (by omega) Qc hid1]
      push_cast
      by_cases h2 : 2 * n < K
      · rw [if_pos h2]
      · rw [if_neg h2]
        rw [Finset.prod_eq_zero (i := K) (Finset.mem_Ioc.mpr ⟨by omega, by omega⟩) (sub_self _)]
        simp
  rw [hfun]
  exact hD
