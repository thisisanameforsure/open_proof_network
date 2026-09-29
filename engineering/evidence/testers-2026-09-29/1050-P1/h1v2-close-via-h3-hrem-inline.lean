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
  -- The statement of hole erdos-1050--h1-v2--h4 (hrem), proved here inline, so that this closing proof
  -- names only the hole erdos-1050--h1-v2--h3 (hden).
  have hrem_all : ∀ (Qc : ℕ → ℕ → ℚ),
      (Qc = fun (n k : ℕ) =>
          ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
              ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
            ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) →
        ∀ (Qx : ℕ → ℚ),
          (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k) →
            ∀ (Aq : ℕ → ℚ),
              (Aq = fun (n : ℕ) =>
                  ∑ k ∈ Finset.range (n + (1 : ℕ)),
                      (∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) *
                        ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
                    Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ))) →
                (∀ (n : ℕ),
                    ∃ (d : ℕ),
                      (0 : ℕ) < d ∧
                        (↑d : ℝ) ^ (2 : ℕ) ≤ (2 : ℝ) ^ ((3 : ℕ) * n * n) ∧
                          (∃ (z : ℤ), (↑z : ℚ) = (↑d : ℚ) * Qx n) ∧ ∃ (z : ℤ), (↑z : ℚ) = (↑d : ℚ) * Aq n) →
                  ∀ (n : ℕ),
                    (0 : ℝ) <
                        (↑(Qx n) : ℝ) * ((3 : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((2 : ℝ) ^ (n + (3 : ℕ)) - (3 : ℝ))) -
                          (↑(Aq n) : ℝ) ∧
                      ((↑(Qx n) : ℝ) * ((3 : ℝ) * ∑' (n : ℕ), (1 : ℝ) / ((2 : ℝ) ^ (n + (3 : ℕ)) - (3 : ℝ))) -
                              (↑(Aq n) : ℝ)) ^
                            (2 : ℕ) *
                          (2 : ℝ) ^ ((4 : ℕ) * n * n) ≤
                        (2 : ℝ) ^ ((2 : ℕ) * n + (4 : ℕ)) := by
    open Polynomial in
    have id1_test : ∀ (n j : ℕ) (hj : j ≤ n),
        (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1)) * ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) =
          ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1) := by
      intro n j hj
      induction j with
      | zero => simp
      | succ j ih =>
        have ih' := ih (by omega)
        rw [Finset.prod_range_succ, ← ih']
        obtain ⟨m, hm⟩ : ∃ m, n - j = m + 1 := ⟨n - j - 1, by omega⟩
        rw [hm, Finset.prod_range_succ, show n - (j + 1) = m by omega]
        ring
    open Polynomial in
    have lower_test : ∀ (j : ℕ),
        ∏ i ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ i) =
          2 ^ (j * (j - 1) / 2) * ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1) := by
      intro j
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
    open Polynomial in
    have upper_test : ∀ (j n : ℕ) (hj : j ≤ n),
        ∏ i ∈ Finset.Ioc j n, ((2 : ℚ) ^ j - 2 ^ i) =
          (-1) ^ (n - j) * 2 ^ (j * (n - j)) * ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) := by
      intro j n hj
      have e : Finset.Ioc j n = Finset.Ico (j + 1) (n + 1) := by
        ext x; simp only [Finset.mem_Ioc, Finset.mem_Ico]; omega
      rw [e, Finset.prod_Ico_eq_prod_range, show n + 1 - (j + 1) = n - j by omega]
      have h1 : ∀ t ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + t)) = (-1) * 2 ^ j * (2 ^ (t + 1) - 1) := by
        intro t _
        rw [show j + 1 + t = j + (t + 1) by ring, pow_add]
        ring
      rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_mul_distrib, Finset.prod_const,
        Finset.prod_const, Finset.card_range, ← pow_mul]
    open Polynomial in
    have rhs_test : ∀ (j n : ℕ) (hj : j ≤ n),
        (∏ K ∈ Finset.Ioc n (2 * n), ((2 : ℚ) ^ j - 2 ^ K)) *
          ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) =
          (-1) ^ n * 2 ^ (j * n) * ∏ s ∈ Finset.range (2 * n - j), ((2 : ℚ) ^ (s + 1) - 1) := by
      intro j n hj
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
    open Polynomial in
    have id1_full : ∀ (n j : ℕ) (hj : j ≤ n),
        (((-1 : ℚ) ^ j * (2 : ℚ) ^ (j * (j - (1 : ℕ)) / (2 : ℕ)) *
              ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
            ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - j - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
          2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
        ∏ K ∈ Finset.Ioc n (2 * n), ((2 : ℚ) ^ j - 2 ^ K) := by
      intro n j hj
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
    clear id1_test lower_test upper_test rhs_test
    open Polynomial in
    have lagr_eval : ∀ (n : ℕ) (x : ℕ → ℚ) (hx : ∀ i ≤ n, ∀ j ≤ n, x i = x j → i = j)
      (N : ℚ[X]) (hNdeg : N.degree ≤ n) (r : ℕ → ℚ)
      (hr : ∀ j ≤ n, r j * ∏ i ∈ (Finset.range (n + 1)).erase j, (x j - x i) = N.eval (x j)),
        N = ∑ j ∈ Finset.range (n + 1), C (r j) * ∏ i ∈ (Finset.range (n + 1)).erase j, (X - C (x i)) := by
      intro n x hx N hNdeg r hr
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
    have tail_coeff : ∀ (n K : ℕ) (hK : n < K) (Qc : ℕ → ℕ → ℚ)
      (hQc : ∀ j ≤ n, Qc n j * 2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
        ∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℚ) ^ j - 2 ^ L)),
        ∑ j ∈ Finset.range (n + 1), Qc n j / ((2 : ℚ) ^ (K - j) - 1) =
          (∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℚ) ^ K - 2 ^ L)) / ∏ i ∈ Finset.range (n + 1), ((2 : ℚ) ^ K - 2 ^ i) := by
      intro n K hK Qc hQc
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
    clear lagr_eval
    open Polynomial in
    have tail3 : ∀ (n : ℕ) (hn : 1 ≤ n),
        ∑' m : ℕ, (3 : ℝ) / (2 ^ (m + n + 1) - 3) = ∑' s : ℕ, ((3 : ℝ) / 2 ^ n) ^ (s + 1) / (2 ^ (s + 1) - 1) := by
      intro n hn
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
    open Polynomial in
    have split3T : ∀ (n : ℕ),
        3 * ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) =
          ∑ j ∈ Finset.range n, (3 : ℝ) / (2 ^ (j + 1) - 3) + ∑' m : ℕ, (3 : ℝ) / (2 ^ (m + n + 1) - 3) := by
      intro n
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
    open Polynomial in
    have cauchy_fin : ∀ (n : ℕ) (q a : ℕ → ℝ) (x A : ℝ) (hA : HasSum (fun s => a s * x ^ (s + 1)) A),
        HasSum (fun K => ∑ j ∈ Finset.range (n + 1), if j < K then q j * a (K - j - 1) * x ^ K else 0)
          ((∑ j ∈ Finset.range (n + 1), q j * x ^ j) * A) := by
      intro n q a x A hA
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
    open Polynomial in
    have h4_series : ∀ (Qc : ℕ → ℕ → ℚ) (hQc : (Qc = fun (n k : ℕ) =>
        ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
            ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
          ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ)))) (Qx : ℕ → ℚ) (hQx : (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k))
      (Aq : ℕ → ℚ) (hAq : (Aq = fun (n : ℕ) =>
                ∑ k ∈ Finset.range (n + (1 : ℕ)),
                    (∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) *
                      ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
                  Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ)))) (n : ℕ) (hn : 1 ≤ n),
        HasSum (fun K : ℕ => if 2 * n < K then
            ((∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L)) / ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i)) *
              ((3 : ℝ) / 2 ^ n) ^ K else 0)
          ((Qx n : ℝ) * (3 * ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3)) - (Aq n : ℝ)) := by
      intro Qc hQc Qx hQx Aq hAq n hn
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
    clear split3T tail3 cauchy_fin tail_coeff id1_full
    open Polynomial in
    have prod_one_sub_ge : ∀ (s : Finset ℕ) (a : ℕ → ℝ) (h0 : ∀ i ∈ s, 0 ≤ a i) (h1 : ∀ i ∈ s, a i ≤ 1),
        1 - ∑ i ∈ s, a i ≤ ∏ i ∈ s, (1 - a i) := by
      intro s a h0 h1
      induction s using Finset.induction_on with
      | empty => simp
      | insert j s hj ih =>
        rw [Finset.sum_insert hj, Finset.prod_insert hj]
        have ih' := ih (fun i hi => h0 i (Finset.mem_insert_of_mem hi)) (fun i hi => h1 i (Finset.mem_insert_of_mem hi))
        have haj0 := h0 j (Finset.mem_insert_self j s)
        have haj1 := h1 j (Finset.mem_insert_self j s)
        have hP : 0 ≤ ∏ i ∈ s, (1 - a i) :=
          Finset.prod_nonneg (fun i hi => by linarith [h1 i (Finset.mem_insert_of_mem hi)])
        have hP1 : ∏ i ∈ s, (1 - a i) ≤ 1 :=
          Finset.prod_le_one (fun i hi => by linarith [h1 i (Finset.mem_insert_of_mem hi)])
            (fun i hi => by linarith [h0 i (Finset.mem_insert_of_mem hi)])
        nlinarith
    open Polynomial in
    have nd_bound : ∀ (n K : ℕ) (hn : 1 ≤ n) (hK : 2 * n + 1 ≤ K),
        0 < (∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L)) / ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i) ∧
        (∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L)) / ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i)
          ≤ 2 * (1 / 2) ^ K := by
      intro n K hn hK
      have hlt : ∀ i, i < K → (0 : ℝ) < 2 ^ K - 2 ^ i := fun i hi => by
        have : (2 : ℝ) ^ i < 2 ^ K := pow_lt_pow_right₀ (by norm_num) hi
        linarith
      have hNpos : 0 < ∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L) :=
        Finset.prod_pos (fun L hL => hlt L (by have := Finset.mem_Ioc.mp hL; omega))
      have hDpos : 0 < ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i) :=
        Finset.prod_pos (fun i hi => hlt i (by have := Finset.mem_range.mp hi; omega))
      refine ⟨div_pos hNpos hDpos, ?_⟩
      have hN : ∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L) ≤ (2 ^ K) ^ n := by
        have := Finset.prod_le_prod (s := Finset.Ioc n (2 * n)) (f := fun L => (2 : ℝ) ^ K - 2 ^ L) (g := fun _ => (2 : ℝ) ^ K)
          (fun L hL => le_of_lt (hlt L (by have := Finset.mem_Ioc.mp hL; omega))) (fun L _ => by
            have : (0 : ℝ) < 2 ^ L := by positivity
            linarith)
        rw [Finset.prod_const, Nat.card_Ioc, show 2 * n - n = n by omega] at this
        exact this
      have hD : (2 ^ K) ^ (n + 1) / 2 ≤ ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i) := by
        have hfac : ∀ i ∈ Finset.range (n + 1), (2 : ℝ) ^ K - 2 ^ i = 2 ^ K * (1 - (1 / 2) ^ (K - i)) := by
          intro i hi
          have hiK : i ≤ K := by have := Finset.mem_range.mp hi; omega
          have e : (2 : ℝ) ^ K = 2 ^ i * 2 ^ (K - i) := by rw [← pow_add]; congr 1; omega
          rw [mul_sub, mul_one, one_div_pow, mul_one_div, e]
          field_simp
        rw [Finset.prod_congr rfl hfac, Finset.prod_mul_distrib, Finset.prod_const, Finset.card_range]
        have hsum : ∑ i ∈ Finset.range (n + 1), ((1 : ℝ) / 2) ^ (K - i) ≤ 1 / 2 := by
          have e : ∀ i ∈ Finset.range (n + 1), ((1 : ℝ) / 2) ^ (K - i) = (1 / 2) ^ (K - n) * (1 / 2) ^ (n - i) := by
            intro i hi
            have := Finset.mem_range.mp hi
            rw [← pow_add]; congr 1; omega
          rw [Finset.sum_congr rfl e, ← Finset.mul_sum]
          have hg : ∑ i ∈ Finset.range (n + 1), ((1 : ℝ) / 2) ^ (n - i) ≤ 2 := by
            have hr := Finset.sum_range_reflect (fun i => ((1 : ℝ) / 2) ^ i) (n + 1)
            simp only [Nat.add_sub_cancel] at hr
            rw [hr]
            exact sum_geometric_two_le (n + 1)
          have hk : ((1 : ℝ) / 2) ^ (K - n) ≤ (1 / 2) ^ 2 :=
            pow_le_pow_of_le_one (by norm_num) (by norm_num) (by omega)
          have hpos : 0 ≤ ((1 : ℝ) / 2) ^ (K - n) := by positivity
          nlinarith
        have hprod := prod_one_sub_ge (Finset.range (n + 1)) (fun i => ((1 : ℝ) / 2) ^ (K - i))
          (fun i _ => by positivity) (fun i _ => pow_le_one₀ (by norm_num) (by norm_num))
        have h2K : (0 : ℝ) < (2 ^ K) ^ (n + 1) := by positivity
        nlinarith
      rw [div_le_iff₀ hDpos]
      have h2K : (2 : ℝ) ^ K * (1 / 2) ^ K = 1 := by rw [← mul_pow]; norm_num
      have e2 : 2 * (1 / 2 : ℝ) ^ K * ((2 ^ K) ^ (n + 1) / 2) = (2 ^ K) ^ n := by
        rw [pow_succ]
        calc 2 * (1 / 2 : ℝ) ^ K * ((2 ^ K) ^ n * 2 ^ K / 2) = (2 ^ K * (1 / 2) ^ K) * (2 ^ K) ^ n := by ring
          _ = (2 ^ K) ^ n := by rw [h2K, one_mul]
      calc ∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L) ≤ (2 ^ K) ^ n := hN
        _ = 2 * (1 / 2) ^ K * ((2 ^ K) ^ (n + 1) / 2) := e2.symm
        _ ≤ 2 * (1 / 2) ^ K * ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i) := by gcongr
    clear prod_one_sub_ge
    open Polynomial in
    have ineq_pow : ∀ (n : ℕ) (hn : 2 ≤ n),
        9 * 81 ^ n ≤ 256 ^ n := by
      intro n hn
      induction n with
      | zero => omega
      | succ m ih =>
        rcases (show m = 1 ∨ 2 ≤ m by omega) with rfl | hm
        · norm_num
        · have := ih hm
          rw [pow_succ, pow_succ]
          omega
    open Polynomial in
    have h4_big : ∀ (Qc : ℕ → ℕ → ℚ) (hQc : (Qc = fun (n k : ℕ) =>
        ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
            ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
          ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ)))) (Qx : ℕ → ℚ) (hQx : (Qx = fun (n : ℕ) => ∑ k ∈ Finset.range (n + (1 : ℕ)), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k))
      (Aq : ℕ → ℚ) (hAq : (Aq = fun (n : ℕ) =>
                ∑ k ∈ Finset.range (n + (1 : ℕ)),
                    (∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ))) *
                      ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
                  Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + (1 : ℕ)) - (3 : ℚ)))) (n : ℕ) (hn : 2 ≤ n),
        (0 : ℝ) < (Qx n : ℝ) * (3 * ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3)) - (Aq n : ℝ) ∧
        ((Qx n : ℝ) * (3 * ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3)) - (Aq n : ℝ)) ^ 2 * (2 : ℝ) ^ (4 * n * n) ≤
          (2 : ℝ) ^ (2 * n + 4) := by
      intro Qc hQc Qx hQx Aq hAq n hn
      have hS := h4_series Qc hQc Qx hQx Aq hAq n (by omega)
      set r := (Qx n : ℝ) * (3 * ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3)) - (Aq n : ℝ) with hr
      set x : ℝ := (3 : ℝ) / 2 ^ n with hxdef
      have hx0 : 0 < x := by positivity
      have hx2 : x / 2 ≤ 3 / 8 := by
        have : (4 : ℝ) ≤ 2 ^ n := by
          calc (4 : ℝ) = 2 ^ 2 := by norm_num
            _ ≤ 2 ^ n := pow_le_pow_right₀ (by norm_num) hn
        rw [hxdef, div_div, div_le_div_iff₀ (by positivity) (by norm_num)]; linarith
      set G : ℕ → ℝ := fun K => if 2 * n < K then
            ((∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L)) / ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i)) *
              x ^ K else 0 with hG
      have hGnn : ∀ K, 0 ≤ G K := by
        intro K; simp only [hG]
        split_ifs with h
        · exact mul_nonneg (le_of_lt (nd_bound n K (by omega) (by omega)).1) (by positivity)
        · exact le_refl 0
      have hGpos : 0 < G (2 * n + 1) := by
        simp only [hG]; rw [if_pos (by omega)]
        exact mul_pos (nd_bound n (2 * n + 1) (by omega) (by omega)).1 (by positivity)
      refine ⟨?_, ?_⟩
      · exact hasSum_lt (f := fun _ => (0 : ℝ)) (g := G) (i := 2 * n + 1) (fun K => hGnn K) hGpos hasSum_zero hS
      · set H : ℕ → ℝ := fun K => if 2 * n < K then 2 * (x / 2) ^ K else 0 with hH
        have hGH : ∀ K, G K ≤ H K := by
          intro K; simp only [hG, hH]
          split_ifs with h
          · have hb := (nd_bound n K (by omega) (by omega)).2
            calc ((∏ L ∈ Finset.Ioc n (2 * n), ((2 : ℝ) ^ K - 2 ^ L)) /
                  ∏ i ∈ Finset.range (n + 1), ((2 : ℝ) ^ K - 2 ^ i)) * x ^ K ≤ 2 * (1 / 2) ^ K * x ^ K := by
                  gcongr
              _ = 2 * (x / 2) ^ K := by ring
          · exact le_refl 0
        have hq : x / 2 < 1 := by linarith
        have hHsum : HasSum H (2 * (x / 2) ^ (2 * n + 1) * (1 - x / 2)⁻¹) := by
          rw [← hasSum_nat_add_iff' (2 * n + 1)]
          have hz : ∑ i ∈ Finset.range (2 * n + 1), H i = 0 :=
            Finset.sum_eq_zero (fun i hi => by
              simp only [hH]; rw [if_neg (by have := Finset.mem_range.mp hi; omega)])
          rw [hz, sub_zero]
          have hgeo := (hasSum_geometric_of_lt_one (by positivity) hq).mul_left (2 * (x / 2) ^ (2 * n + 1))
          have hfun : (fun s => H (s + (2 * n + 1))) = fun s => 2 * (x / 2) ^ (2 * n + 1) * (x / 2) ^ s := by
            funext s; simp only [hH]; rw [if_pos (by omega), pow_add]; ring
          rw [hfun]
          exact hgeo
        have hrle : r ≤ 2 * (x / 2) ^ (2 * n + 1) * (1 - x / 2)⁻¹ := hasSum_le hGH hS hHsum
        have hr0 : 0 ≤ r := le_of_lt (hasSum_lt (f := fun _ => (0 : ℝ)) (g := G) (i := 2 * n + 1)
          (fun K => hGnn K) hGpos hasSum_zero hS)
        have hr8 : r ≤ 8 * (x / 2) ^ (2 * n + 1) := by
          have hinv : (1 - x / 2)⁻¹ ≤ 4 := by
            rw [inv_le_comm₀ (by linarith) (by norm_num)]; linarith
          have hp : 0 ≤ 2 * (x / 2) ^ (2 * n + 1) := by positivity
          calc r ≤ 2 * (x / 2) ^ (2 * n + 1) * (1 - x / 2)⁻¹ := hrle
            _ ≤ 2 * (x / 2) ^ (2 * n + 1) * 4 := by gcongr
            _ = 8 * (x / 2) ^ (2 * n + 1) := by ring
        have hsq : r ^ 2 ≤ (8 * (x / 2) ^ (2 * n + 1)) ^ 2 := pow_le_pow_left₀ hr0 hr8 2
        have hnat : 64 * 3 ^ (4 * n + 2) * 2 ^ (4 * n * n) ≤ 2 ^ (2 * n + 4) * (2 ^ (n + 1)) ^ (4 * n + 2) := by
          have e1 : (2 : ℕ) ^ (2 * n + 4) * (2 ^ (n + 1)) ^ (4 * n + 2) = 2 ^ (4 * n * n) * (64 * 256 ^ n) := by
            rw [← pow_mul, ← pow_add, show (256 : ℕ) = 2 ^ 8 by norm_num, ← pow_mul,
              show (64 : ℕ) = 2 ^ 6 by norm_num, ← pow_add, ← pow_add]
            congr 1; ring
          have e2 : 64 * 3 ^ (4 * n + 2) * 2 ^ (4 * n * n) = 2 ^ (4 * n * n) * (64 * (9 * 81 ^ n)) := by
            rw [show (81 : ℕ) = 3 ^ 4 by norm_num, ← pow_mul, pow_add]; ring
          rw [e1, e2]
          have := ineq_pow n hn
          gcongr
        have hreal : (64 : ℝ) * 3 ^ (4 * n + 2) * 2 ^ (4 * n * n) ≤ 2 ^ (2 * n + 4) * (2 ^ (n + 1)) ^ (4 * n + 2) := by
          exact_mod_cast hnat
        have hx2' : x / 2 = 3 / 2 ^ (n + 1) := by rw [hxdef, pow_succ]; field_simp
        have hsq' : r ^ 2 ≤ 64 * (x / 2) ^ (4 * n + 2) := by
          calc r ^ 2 ≤ (8 * (x / 2) ^ (2 * n + 1)) ^ 2 := hsq
            _ = 64 * (x / 2) ^ (4 * n + 2) := by ring
        have hkey : (x / 2) ^ (4 * n + 2) * ((2 : ℝ) ^ (n + 1)) ^ (4 * n + 2) = 3 ^ (4 * n + 2) := by
          rw [← mul_pow, hx2', div_mul_cancel₀ _ (by positivity)]
        have hP : (0 : ℝ) < ((2 : ℝ) ^ (n + 1)) ^ (4 * n + 2) := by positivity
        have hmain : 64 * (x / 2) ^ (4 * n + 2) * (2 : ℝ) ^ (4 * n * n) ≤ 2 ^ (2 * n + 4) := by
          refine le_of_mul_le_mul_right ?_ hP
          calc 64 * (x / 2) ^ (4 * n + 2) * (2 : ℝ) ^ (4 * n * n) * ((2 : ℝ) ^ (n + 1)) ^ (4 * n + 2)
              = 64 * 3 ^ (4 * n + 2) * 2 ^ (4 * n * n) := by rw [← hkey]; ring
            _ ≤ 2 ^ (2 * n + 4) * ((2 : ℝ) ^ (n + 1)) ^ (4 * n + 2) := hreal
        calc r ^ 2 * (2 : ℝ) ^ (4 * n * n) ≤ 64 * (x / 2) ^ (4 * n + 2) * 2 ^ (4 * n * n) := by gcongr
          _ ≤ 2 ^ (2 * n + 4) := hmain
    open Polynomial in
    clear h4_series nd_bound ineq_pow
    have T_facts : Summable (fun m : ℕ => (1 : ℝ) / (2 ^ (m + 3) - 3)) ∧
        0 < ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) ∧ ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) ≤ 2 / 5 := by
      have h5 : ∀ m : ℕ, 5 * (2 : ℝ) ^ m ≤ 2 ^ (m + 3) - 3 := by
        intro m
        have h1 : (1 : ℝ) ≤ 2 ^ m := one_le_pow₀ (by norm_num)
        have e : (2 : ℝ) ^ (m + 3) = 8 * 2 ^ m := by rw [pow_add]; norm_num; ring
        rw [e]; linarith
      have hpos : ∀ m : ℕ, 0 < (2 : ℝ) ^ (m + 3) - 3 := fun m => by
        have := h5 m; have : (0 : ℝ) < 2 ^ m := by positivity
        linarith
      have hle : ∀ m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) ≤ (1 / 5) * (1 / 2) ^ m := by
        intro m
        have e : (1 / 5 : ℝ) * (1 / 2) ^ m = 1 / (5 * 2 ^ m) := by
          rw [one_div_pow]; field_simp
        rw [e]
        exact one_div_le_one_div_of_le (by positivity) (h5 m)
      have hs : Summable (fun m : ℕ => (1 : ℝ) / (2 ^ (m + 3) - 3)) :=
        Summable.of_nonneg_of_le (fun m => le_of_lt (one_div_pos.mpr (hpos m))) hle
          (summable_geometric_two.mul_left (1 / 5))
      refine ⟨hs, ?_, ?_⟩
      · exact hs.tsum_pos (fun m => le_of_lt (one_div_pos.mpr (hpos m))) 0 (one_div_pos.mpr (hpos 0))
      · calc ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) ≤ ∑' m : ℕ, (1 / 5 : ℝ) * (1 / 2) ^ m :=
              hs.tsum_le_tsum hle (summable_geometric_two.mul_left (1 / 5))
          _ = 2 / 5 := by rw [tsum_mul_left, tsum_geometric_two]; norm_num
    obtain ⟨_, hTpos, hTle⟩ := T_facts
    intro Qc hQc Qx hQx Aq hAq _ n
    match n with
    | 0 =>
      have hQx0 : Qx 0 = 1 := by rw [hQx, hQc]; simp
      have hAq0 : Aq 0 = 0 := by rw [hAq]; simp
      rw [hQx0, hAq0]
      push_cast
      set T := ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) with hT
      refine ⟨by linarith, ?_⟩
      have e : ((1 : ℝ) * (3 * T) - 0) ^ 2 * (2 : ℝ) ^ (4 * 0 * 0) = 9 * (T * T) := by ring
      rw [e]
      norm_num
      nlinarith
    | 1 =>
      -- Qx 1 = 3 - 3/2 = 3/2 and Aq 1 = 3 * (3/2) + (3/2) * (3/(2-3)) = 0, so the remainder is (9/2) T.
      have hQx1 : Qx 1 = 3 / 2 := by
        rw [hQx, hQc]; norm_num [Finset.sum_range_succ, Finset.prod_range_succ]
      have hAq1 : Aq 1 = 0 := by
        rw [hAq]; simp only [hQx1]; rw [hQc]
        norm_num [Finset.sum_range_succ, Finset.prod_range_succ]
      rw [hQx1, hAq1]
      push_cast
      set T := ∑' m : ℕ, (1 : ℝ) / (2 ^ (m + 3) - 3) with hT
      refine ⟨by nlinarith, ?_⟩
      norm_num
      nlinarith
    | n + 2 => exact h4_big Qc hQc Qx hQx Aq hAq (n + 2) (by omega)
  -- Informal account: annex f593a93a8960 (graph PR #185) on this node.
  -- Explicit q-Pade approximants (Borwein's route) for T = f(3)/3, f(x) = sum_j x/(2^j - x),
  -- evaluated at x_n = 3/2^n.  Qc n k: the Pade denominator's coefficients; Qx n = Q_n(x_n);
  -- Aq n = P_n(x_n) + Q_n(x_n) * c_n with c_n = sum_{j<n} 3/(2^(j+1) - 3).
  obtain ⟨Qc, hQc⟩ : ∃ Qc : ℕ → ℕ → ℚ, Qc = fun n k => (-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - 1) / 2) *
      (∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
      (∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - k - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) :=
    ⟨_, rfl⟩
  obtain ⟨Qx, hQx⟩ : ∃ Qx : ℕ → ℚ, Qx = fun n =>
      ∑ k ∈ Finset.range (n + 1), Qc n k * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k := ⟨_, rfl⟩
  obtain ⟨Aq, hAq⟩ : ∃ Aq : ℕ → ℚ, Aq = fun n =>
      ∑ k ∈ Finset.range (n + 1),
          (∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1)) * ((3 : ℚ) / (2 : ℚ) ^ n) ^ k +
        Qx n * ∑ j ∈ Finset.range n, (3 : ℚ) / ((2 : ℚ) ^ (j + 1) - 3) := ⟨_, rfl⟩
  -- Borwein's arithmetic estimate: a common denominator of size at most 2^(3n^2/2).
  have hden : ∀ n : ℕ, ∃ d : ℕ, 0 < d ∧ ((d : ℝ)) ^ 2 ≤ (2 : ℝ) ^ (3 * n * n) ∧
      (∃ z : ℤ, (z : ℚ) = d * Qx n) ∧ ∃ z : ℤ, (z : ℚ) = d * Aq n :=
    erdos_1050__h1_v2__h3 Qc hQc Qx hQx Aq hAq
  -- Borwein's analytic estimate: the remainder Q_n(x_n) f(x_n) - P_n(x_n) is positive and about 2^(-2n^2).
  have hrem : ∀ n : ℕ,
      0 < (Qx n : ℝ) * (3 * ∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - (Aq n : ℝ) ∧
      ((Qx n : ℝ) * (3 * ∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - (Aq n : ℝ)) ^ 2 *
        (2 : ℝ) ^ (4 * n * n) ≤ (2 : ℝ) ^ (2 * n + 4) :=
    hrem_all Qc hQc Qx hQx Aq hAq hden
  choose d hd0 hdb hz using hden
  choose b hb using fun n => (hz n).1
  choose a ha using fun n => (hz n).2
  refine ⟨a, fun n => 3 * b n, ?_⟩
  have key : ∀ n : ℕ, (((3 * b n : ℤ)) : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - a n =
      (d n : ℝ) * ((Qx n : ℝ) * (3 * ∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - (Aq n : ℝ)) := by
    intro n
    have hb' : (b n : ℝ) = (d n : ℝ) * (Qx n : ℝ) := by exact_mod_cast hb n
    have ha' : (a n : ℝ) = (d n : ℝ) * (Aq n : ℝ) := by exact_mod_cast ha n
    push_cast
    rw [hb', ha']
    ring
  have pos : ∀ n : ℕ, 0 < (((3 * b n : ℤ)) : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - a n := by
    intro n
    rw [key n]
    exact mul_pos (by exact_mod_cast hd0 n) (hrem n).1
  refine ⟨fun n => (pos n).ne', ?_⟩
  set e : ℕ → ℝ := fun n => (((3 * b n : ℤ)) : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - a n
    with he
  have bound : ∀ n : ℕ, e n ^ 2 ≤ 64 * (1 / 2 : ℝ) ^ n := by
    intro n
    have h1 : e n ^ 2 * (2 : ℝ) ^ (4 * n * n) ≤ (2 : ℝ) ^ (3 * n * n) * (2 : ℝ) ^ (2 * n + 4) := by
      simp only [he]
      rw [key n, mul_pow, mul_assoc]
      exact mul_le_mul (hdb n) (hrem n).2 (by positivity) (by positivity)
    have h2 : (2 : ℝ) ^ (4 * n * n) = (2 : ℝ) ^ (n * n) * (2 : ℝ) ^ (3 * n * n) := by
      rw [← pow_add]; ring_nf
    have h3 : e n ^ 2 * (2 : ℝ) ^ (n * n) ≤ (2 : ℝ) ^ (2 * n + 4) := by
      have hp : (0 : ℝ) < (2 : ℝ) ^ (3 * n * n) := by positivity
      rw [h2] at h1
      nlinarith
    have h4 : (2 : ℝ) ^ (2 * n + 4) * 2 ^ n ≤ 64 * (2 : ℝ) ^ (n * n) := by
      have : 3 * n + 4 ≤ n * n + 6 := by nlinarith [sq_nonneg ((n : ℤ) - 2)]
      calc (2 : ℝ) ^ (2 * n + 4) * 2 ^ n = 2 ^ (3 * n + 4) := by rw [← pow_add]; ring_nf
        _ ≤ 2 ^ (n * n + 6) := pow_le_pow_right₀ (by norm_num) this
        _ = 64 * (2 : ℝ) ^ (n * n) := by rw [pow_add]; norm_num; ring
    have hpn : (0 : ℝ) < (2 : ℝ) ^ n := by positivity
    have hpnn : (0 : ℝ) < (2 : ℝ) ^ (n * n) := by positivity
    rw [one_div_pow, mul_one_div, le_div_iff₀ hpn]
    nlinarith
  have hsq : Filter.Tendsto (fun n => e n ^ 2) Filter.atTop (nhds 0) := by
    refine squeeze_zero (fun n => sq_nonneg _) bound ?_
    simpa using (tendsto_pow_atTop_nhds_zero_of_lt_one (by norm_num : (0 : ℝ) ≤ 1 / 2)
      (by norm_num)).const_mul 64
  have := hsq.sqrt
  simp only [Real.sqrt_zero] at this
  refine this.congr (fun n => ?_)
  exact Real.sqrt_sq (pos n).le
