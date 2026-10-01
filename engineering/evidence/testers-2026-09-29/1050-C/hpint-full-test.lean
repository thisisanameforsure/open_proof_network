import Mathlib

theorem hpint_test : ∀ (Qc : ℕ → ℕ → ℚ),
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
            ∀ (n : ℕ) (M : ℕ → ℕ),
              (M = fun (n : ℕ) => ∏ m ∈ Finset.Ioc (n / (2 : ℕ)) n, ((2 : ℕ) ^ m - (1 : ℕ))) →
                ∀ (C : ℕ → ℕ),
                  (C = fun (n : ℕ) => ∏ j ∈ Finset.Ico (2 : ℕ) n, ((2 : ℕ) ^ (j + (1 : ℕ)) - (3 : ℕ))) →
                    (∀ k ≤ n, ∃ (z : ℤ), (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) = Qc n k) →
                      ∀ k ≤ n,
                        ∃ (z : ℤ),
                          (↑z : ℚ) * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) =
                            (↑(M n) : ℚ) * ∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ)) := by
  intro Qc hQc Qx _ Aq _ n M hM C _ hQcint k hk
  -- the closed form of p_k (spec-ffd3137a's statement), proved: Lagrange coefficients, interpolation,
  -- and the derivative at a node
  have hclosedAll : ∀ (Qc : ℕ → ℕ → ℚ),
      (Qc = fun (n k : ℕ) =>
        ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - 1) / 2) *
            ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
          ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - k - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) →
      ∀ n k : ℕ, k ≤ n →
        ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1) =
          Qc n k * (∑ i ∈ Finset.range n, 1 / (1 - (2 : ℚ) ^ (n + 1 + i - k)) -
              ∑ b ∈ Finset.range k, (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) -
              ∑ b ∈ Finset.range (n - k), 1 / (1 - (2 : ℚ) ^ (b + 1))) +
            ∑ b ∈ Finset.range (n - k), Qc n (k + b + 1) * (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := by
    have lag_test : ∀ (n j : ℕ), j ≤ n →
          (((-1 : ℚ) ^ j * (2 : ℚ) ^ (j * (j - 1) / 2) *
            ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
          ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - j - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) * 2 ^ j *
          (∏ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l)) *
          ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s)) =
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ j - 2 ^ (n + 1 + i)) := by
      intro n j hj
      have hpos : ∀ s : ℕ, (2 : ℚ) ^ (s + 1) - 1 ≠ 0 := by
        intro s
        have : (2 : ℚ) ≤ 2 ^ (s + 1) := by
          calc (2 : ℚ) = 2 ^ 1 := by norm_num
            _ ≤ 2 ^ (s + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
        linarith
      -- (b) the nodes below j
      have hb : ∏ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l) =
          (2 : ℚ) ^ (j * (j - 1) / 2) * ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1) := by
        have h1 : ∀ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l) = 2 ^ l * ((2 : ℚ) ^ (j - l) - 1) := by
          intro l hl
          have hl' := Finset.mem_range.mp hl
          have : (2 : ℚ) ^ j = 2 ^ l * 2 ^ (j - l) := by rw [← pow_add]; congr 1; omega
          rw [this]; ring
        rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_pow_eq_pow_sum,
          Finset.sum_range_id]
        congr 1
        rw [← Finset.prod_range_reflect]
        refine Finset.prod_congr rfl (fun s hs => ?_)
        have hs' := Finset.mem_range.mp hs
        congr 2
        omega
      -- (c) the nodes above j
      have hc : ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s)) =
          (-(2 : ℚ) ^ j) ^ (n - j) * ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) := by
        calc ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s))
            = ∏ s ∈ Finset.range (n - j), ((-(2 : ℚ) ^ j) * ((2 : ℚ) ^ (s + 1) - 1)) := by
              refine Finset.prod_congr rfl (fun s _ => ?_)
              rw [show j + 1 + s = j + (s + 1) by omega, pow_add]
              ring
          _ = _ := by rw [Finset.prod_mul_distrib, Finset.prod_const, Finset.card_range]
      -- (d) the right side
      have hd : ∏ i ∈ Finset.range n, ((2 : ℚ) ^ j - 2 ^ (n + 1 + i)) =
          (-(2 : ℚ) ^ j) ^ n * ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (n + 1 + i - j) - 1) := by
        calc ∏ i ∈ Finset.range n, ((2 : ℚ) ^ j - 2 ^ (n + 1 + i))
            = ∏ i ∈ Finset.range n, ((-(2 : ℚ) ^ j) * ((2 : ℚ) ^ (n + 1 + i - j) - 1)) := by
              refine Finset.prod_congr rfl (fun i _ => ?_)
              rw [show n + 1 + i = j + (n + 1 + i - j) by omega, pow_add, Nat.add_sub_cancel_left]
              ring
          _ = _ := by rw [Finset.prod_mul_distrib, Finset.prod_const, Finset.card_range]
      -- (e) the q-factorial splits at j
      have he : (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1)) *
          ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ (s + 1) - 1) =
          ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1) := by
        have hn : n = (n - j) + j := by omega
        conv_rhs => rw [hn]
        rw [Finset.prod_range_add, mul_comm]
        congr 1
        rw [← Finset.prod_range_reflect]
        refine Finset.prod_congr rfl (fun t ht => ?_)
        have ht' := Finset.mem_range.mp ht
        congr 2
        omega
      -- (f) reflect the second Gaussian binomial's numerator
      have hf : ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - j - i) - 1) =
          ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (n + 1 + i - j) - 1) := by
        rw [← Finset.prod_range_reflect]
        refine Finset.prod_congr rfl (fun i hi => ?_)
        have hi' := Finset.mem_range.mp hi
        congr 2
        omega
      have hF : ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1) ≠ 0 :=
        Finset.prod_ne_zero_iff.mpr (fun s _ => hpos s)
      have hB : ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1) ≠ 0 :=
        Finset.prod_ne_zero_iff.mpr (fun s _ => hpos s)
      have hjj : j * j = j * (j - 1) / 2 + j * (j - 1) / 2 + j := by
        have h2 := Nat.two_mul_div_two_of_even (Nat.even_mul_pred_self j)
        rcases j with _ | j
        · simp
        · simp only [Nat.add_sub_cancel] at h2 ⊢
          nlinarith
      have hpow : (-(2 : ℚ) ^ j) ^ n = (-1) ^ j * 2 ^ (j * (j - 1) / 2) * 2 ^ (j * (j - 1) / 2) * 2 ^ j *
          (-(2 : ℚ) ^ j) ^ (n - j) := by
        rw [show n = j + (n - j) by omega, pow_add, Nat.add_sub_cancel_left, neg_pow, ← pow_mul, hjj,
          pow_add, pow_add]
        ring
      rw [Finset.prod_div_distrib, Finset.prod_div_distrib, hb, hc, hd, hf, hpow]
      field_simp
      rw [← he]
      ring
    open Polynomial in
    have pf_test : ∀ (n : ℕ) (x y w : ℕ → ℚ), (∀ a ∈ Finset.range (n + 1), ∀ b ∈ Finset.range (n + 1), x a = x b → a = b) →
          (∀ j ∈ Finset.range (n + 1),
            w j * ∏ l ∈ (Finset.range (n + 1)).erase j, (x j - x l) = ∏ i ∈ Finset.range n, (x j - y i)) →
          (∑ j ∈ Finset.range (n + 1), Polynomial.C (w j) * ∏ l ∈ (Finset.range (n + 1)).erase j, (X - Polynomial.C (x l))) =
          ∏ i ∈ Finset.range n, (X - Polynomial.C (y i)) := by
      intro n x y w hx hw
      set s := Finset.range (n + 1) with hs
      have hL : (∑ j ∈ s, Polynomial.C (w j) * ∏ l ∈ s.erase j, (X - Polynomial.C (x l))).natDegree ≤ n := by
        refine natDegree_sum_le_of_forall_le _ _ (fun j hj => ?_)
        refine (natDegree_C_mul_le _ _).trans ((natDegree_prod_le _ _).trans ?_)
        simp only [natDegree_X_sub_C, Finset.sum_const, smul_eq_mul, mul_one]
        rw [Finset.card_erase_of_mem hj, hs, Finset.card_range]
        omega
      have hE : (∏ i ∈ Finset.range n, (X - Polynomial.C (y i))).natDegree ≤ n := by
        refine (natDegree_prod_le _ _).trans ?_
        simp [natDegree_X_sub_C]
      apply Polynomial.eq_of_degree_sub_lt_of_eval_finset_eq (s.image x)
      · rw [Finset.card_image_of_injOn (fun a ha b hb h => hx a ha b hb h), hs, Finset.card_range]
        refine lt_of_le_of_lt (degree_sub_le _ _) (max_lt ?_ ?_)
        · exact lt_of_le_of_lt (degree_le_of_natDegree_le hL) (by exact_mod_cast Nat.lt_succ_self n)
        · exact lt_of_le_of_lt (degree_le_of_natDegree_le hE) (by exact_mod_cast Nat.lt_succ_self n)
      · intro z hz
        obtain ⟨j, hj, rfl⟩ := Finset.mem_image.mp hz
        simp only [eval_finset_sum, eval_mul, eval_C, eval_prod, eval_sub, eval_X]
        rw [Finset.sum_eq_single j]
        · exact hw j hj
        · intro i hi hij
          rw [Finset.prod_eq_zero (i := j) (Finset.mem_erase.mpr ⟨Ne.symm hij, hj⟩) (sub_self _), mul_zero]
        · intro hj'; exact absurd hj hj'
    open Polynomial in
    have pf2_test : ∀ (n k : ℕ), k ∈ Finset.range (n + 1) → ∀ (x y w : ℕ → ℚ),
          (∀ a ∈ Finset.range (n + 1), ∀ b ∈ Finset.range (n + 1), x a = x b → a = b) →
          (∀ i ∈ Finset.range n, x k - y i ≠ 0) →
          (∀ j ∈ Finset.range (n + 1),
            w j * ∏ l ∈ (Finset.range (n + 1)).erase j, (x j - x l) = ∏ i ∈ Finset.range n, (x j - y i)) →
          ∑ j ∈ (Finset.range (n + 1)).erase k, w j / (x k - x j) =
          w k * (∑ i ∈ Finset.range n, 1 / (x k - y i) -
            ∑ l ∈ (Finset.range (n + 1)).erase k, 1 / (x k - x l)) := by
      intro n k hk x y w hx hxy hw
      have hLE := pf_test n x y w hx hw
      set s := Finset.range (n + 1) with hs
      have hne : ∀ j ∈ s, j ≠ k → x k - x j ≠ 0 := by
        intro j hj hjk h
        exact hjk (hx j hj k hk (sub_eq_zero.mp h).symm)
      set P := ∏ l ∈ s.erase k, (x k - x l) with hP
      have hP0 : P ≠ 0 := Finset.prod_ne_zero_iff.mpr (fun l hl =>
        hne l (Finset.mem_of_mem_erase hl) (Finset.ne_of_mem_erase hl))
      have hd := congrArg (fun p => (derivative p).eval (x k)) hLE
      simp only [derivative_sum, derivative_mul, derivative_C, zero_mul, zero_add, derivative_prod_finset,
        derivative_sub, derivative_X, sub_zero, mul_one, eval_finset_sum, eval_mul, eval_C, eval_prod,
        eval_sub, eval_X] at hd
      -- the terms j ≠ k
      have h1 : ∀ j ∈ s.erase k, (∑ m ∈ s.erase j, ∏ l ∈ (s.erase j).erase m, (x k - x l)) =
          P * (1 / (x k - x j)) := by
        intro j hj
        have hjs := Finset.mem_of_mem_erase hj
        have hjk := Finset.ne_of_mem_erase hj
        have hks : k ∈ s.erase j := Finset.mem_erase.mpr ⟨Ne.symm hjk, hk⟩
        rw [Finset.sum_eq_single k]
        · have := Finset.mul_prod_erase (s.erase k) (fun l => x k - x l) hj
          rw [Finset.erase_right_comm]
          field_simp [hne j hjs hjk]
          rw [hP, ← this]
          ring
        · intro m hm hmk
          exact Finset.prod_eq_zero (i := k) (Finset.mem_erase.mpr ⟨Ne.symm hmk, hks⟩) (sub_self _)
        · intro h; exact absurd hks h
      -- the term j = k
      have h2 : (∑ m ∈ s.erase k, ∏ l ∈ (s.erase k).erase m, (x k - x l)) =
          P * ∑ m ∈ s.erase k, 1 / (x k - x m) := by
        rw [Finset.mul_sum]
        refine Finset.sum_congr rfl (fun m hm => ?_)
        have := Finset.mul_prod_erase (s.erase k) (fun l => x k - x l) hm
        field_simp [hne m (Finset.mem_of_mem_erase hm) (Finset.ne_of_mem_erase hm)]
        rw [hP, ← this]
        ring
      -- the right side
      have h3 : (∑ i ∈ Finset.range n, ∏ i' ∈ (Finset.range n).erase i, (x k - y i')) =
          (w k * P) * ∑ i ∈ Finset.range n, 1 / (x k - y i) := by
        rw [hw k hk, Finset.mul_sum]
        refine Finset.sum_congr rfl (fun i hi => ?_)
        have := Finset.mul_prod_erase (Finset.range n) (fun i' => x k - y i') hi
        field_simp [hxy i hi]
        rw [← this]
        ring
      rw [← Finset.add_sum_erase s _ hk, h2, h3] at hd
      have h1' : ∑ j ∈ s.erase k, w j * ∑ m ∈ s.erase j, ∏ l ∈ (s.erase j).erase m, (x k - x l) =
          P * ∑ j ∈ s.erase k, w j / (x k - x j) := by
        rw [Finset.mul_sum]
        refine Finset.sum_congr rfl (fun j hj => ?_)
        rw [h1 j hj]
        ring
      rw [h1'] at hd
      apply mul_left_cancel₀ hP0
      linear_combination hd
    intro Qc hQc n k hk
    have hc : ∀ j, Qc n j = ((-1 : ℚ) ^ j * (2 : ℚ) ^ (j * (j - 1) / 2) *
          ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
        ∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - j - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
      intro j; rw [hQc]
    have hk1 : k ∈ Finset.range (n + 1) := Finset.mem_range.mpr (by omega)
    have h2 : ∀ m : ℕ, (2 : ℚ) ^ m ≠ 0 := fun m => by positivity
    have hs1 : ∀ b : ℕ, (2 : ℚ) ^ (b + 1) - 1 ≠ 0 := by
      intro b
      have : (2 : ℚ) ≤ 2 ^ (b + 1) := by
        calc (2 : ℚ) = 2 ^ 1 := by norm_num
          _ ≤ 2 ^ (b + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
      linarith
    have hs1' : ∀ b : ℕ, (1 : ℚ) - 2 ^ (b + 1) ≠ 0 := fun b h => hs1 b (by linarith)
    have hinj : ∀ a b : ℕ, (2 : ℚ) ^ a = 2 ^ b → a = b := by
      intro a b h
      have : (2 : ℕ) ^ a = 2 ^ b := by exact_mod_cast h
      exact Nat.pow_right_injective (le_refl 2) this
    have hx : ∀ a ∈ Finset.range (n + 1), ∀ b ∈ Finset.range (n + 1),
        (fun l : ℕ => (2 : ℚ) ^ l) a = (fun l : ℕ => (2 : ℚ) ^ l) b → a = b :=
      fun a _ b _ h => hinj a b h
    have hxy : ∀ i ∈ Finset.range n,
        (fun l : ℕ => (2 : ℚ) ^ l) k - (fun i : ℕ => (2 : ℚ) ^ (n + 1 + i)) i ≠ 0 := by
      intro i _ h
      have := hinj _ _ (sub_eq_zero.mp h)
      omega
    have hw : ∀ j ∈ Finset.range (n + 1),
        (fun j => Qc n j * (2 : ℚ) ^ j) j *
          ∏ l ∈ (Finset.range (n + 1)).erase j, ((fun l : ℕ => (2 : ℚ) ^ l) j - (fun l : ℕ => (2 : ℚ) ^ l) l) =
        ∏ i ∈ Finset.range n, ((fun l : ℕ => (2 : ℚ) ^ l) j - (fun i : ℕ => (2 : ℚ) ^ (n + 1 + i)) i) := by
      intro j hj
      have hjn : j ≤ n := Nat.lt_succ_iff.mp (Finset.mem_range.mp hj)
      simp only []
      let g : ℕ → ℚ := fun l => if l = j then 1 else (2 : ℚ) ^ j - 2 ^ l
      have e1 : ∏ l ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ l) =
          ∏ l ∈ (Finset.range (n + 1)).erase j, g l :=
        Finset.prod_congr rfl (fun l hl => by simp [g, Finset.ne_of_mem_erase hl])
      have e2 : ∏ l ∈ (Finset.range (n + 1)).erase j, g l = ∏ l ∈ Finset.range (n + 1), g l :=
        Finset.prod_erase _ (by simp [g])
      have e3 : ∏ l ∈ Finset.range (n + 1), g l =
          (∏ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l)) *
            ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s)) := by
        rw [show n + 1 = (j + 1) + (n - j) by omega, Finset.prod_range_add, Finset.prod_range_succ]
        have ga : ∏ l ∈ Finset.range j, g l = ∏ l ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ l) :=
          Finset.prod_congr rfl (fun l hl => by
            have := Finset.mem_range.mp hl
            simp [g, show l ≠ j by omega])
        have gb : ∏ s ∈ Finset.range (n - j), g (j + 1 + s) =
            ∏ s ∈ Finset.range (n - j), ((2 : ℚ) ^ j - 2 ^ (j + 1 + s)) :=
          Finset.prod_congr rfl (fun s _ => by simp [g, show j + 1 + s ≠ j by omega])
        rw [ga, gb]
        simp [g]
      rw [e1, e2, e3, ← lag_test n j hjn, hc j]
      ring
    have hpf := pf2_test n k hk1 (fun l : ℕ => (2 : ℚ) ^ l) (fun i : ℕ => (2 : ℚ) ^ (n + 1 + i))
      (fun j => Qc n j * (2 : ℚ) ^ j) hx hxy hw
    beta_reduce at hpf
    have hpk : ∀ j, j < k → (2 : ℚ) ^ (k - j) - 1 ≠ 0 := by
      intro j hj
      rw [show k - j = (k - j - 1) + 1 by omega]
      exact hs1 _
    -- T0: the j = k term of the statement's sum is 0
    have T0 : ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1) =
        ∑ j ∈ Finset.range k, Qc n j / ((2 : ℚ) ^ (k - j) - 1) := by
      rw [Finset.sum_range_succ, Nat.sub_self, pow_zero, sub_self, div_zero, add_zero]
    -- T1: the left side of hpf
    have T1 : ∑ j ∈ (Finset.range (n + 1)).erase k, Qc n j * (2 : ℚ) ^ j / ((2 : ℚ) ^ k - 2 ^ j) =
        ∑ j ∈ Finset.range k, Qc n j / ((2 : ℚ) ^ (k - j) - 1) -
          ∑ b ∈ Finset.range (n - k), Qc n (k + b + 1) * (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := by
      let G : ℕ → ℚ := fun j => if j = k then 0 else Qc n j * (2 : ℚ) ^ j / ((2 : ℚ) ^ k - 2 ^ j)
      have e1 : ∑ j ∈ (Finset.range (n + 1)).erase k, Qc n j * (2 : ℚ) ^ j / ((2 : ℚ) ^ k - 2 ^ j) =
          ∑ j ∈ (Finset.range (n + 1)).erase k, G j :=
        Finset.sum_congr rfl (fun j hj => by simp [G, Finset.ne_of_mem_erase hj])
      rw [e1, Finset.sum_erase _ (by simp [G]),
        show n + 1 = (k + 1) + (n - k) by omega, Finset.sum_range_add, Finset.sum_range_succ]
      have ga : ∑ j ∈ Finset.range k, G j = ∑ j ∈ Finset.range k, Qc n j / ((2 : ℚ) ^ (k - j) - 1) := by
        refine Finset.sum_congr rfl (fun j hj => ?_)
        have hjk := Finset.mem_range.mp hj
        simp only [G, show j ≠ k by omega, if_false]
        rw [show (2 : ℚ) ^ k = 2 ^ j * 2 ^ (k - j) by rw [← pow_add]; congr 1; omega]
        field_simp [h2 j, hpk j hjk]
      have gb : ∑ b ∈ Finset.range (n - k), G (k + 1 + b) =
          -∑ b ∈ Finset.range (n - k), Qc n (k + b + 1) * (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := by
        rw [← Finset.sum_neg_distrib]
        refine Finset.sum_congr rfl (fun b _ => ?_)
        simp only [G]
        rw [if_neg (by omega : k + 1 + b ≠ k), show k + 1 + b = k + b + 1 by omega]
        rw [show (2 : ℚ) ^ (k + b + 1) = 2 ^ k * 2 ^ (b + 1) by
          rw [show k + b + 1 = k + (b + 1) by omega, pow_add]]
        have : (2 : ℚ) ^ k - 2 ^ k * 2 ^ (b + 1) = -(2 ^ k * (2 ^ (b + 1) - 1)) := by ring
        rw [this]
        field_simp [h2 k, hs1 b]
      rw [ga, gb]
      simp [G]
      ring
    -- T2: the nodes 2^(n+1+i)
    have T2 : Qc n k * (2 : ℚ) ^ k * ∑ i ∈ Finset.range n, 1 / ((2 : ℚ) ^ k - 2 ^ (n + 1 + i)) =
        Qc n k * ∑ i ∈ Finset.range n, 1 / (1 - (2 : ℚ) ^ (n + 1 + i - k)) := by
      rw [mul_assoc, Finset.mul_sum, Finset.mul_sum, Finset.mul_sum]
      refine Finset.sum_congr rfl (fun i _ => ?_)
      have e : n + 1 + i - k = (n - k + i) + 1 := by omega
      rw [show (2 : ℚ) ^ (n + 1 + i) = 2 ^ k * 2 ^ (n + 1 + i - k) by rw [← pow_add]; congr 1; omega, e]
      have : (2 : ℚ) ^ k - 2 ^ k * 2 ^ (n - k + i + 1) = 2 ^ k * (1 - 2 ^ (n - k + i + 1)) := by ring
      rw [this]
      field_simp [h2 k, hs1' (n - k + i)] <;> ring
    -- T3: the other nodes 2^l, l ≠ k
    have T3a : ∑ l ∈ (Finset.range (n + 1)).erase k, 1 / ((2 : ℚ) ^ k - 2 ^ l) =
        ∑ l ∈ Finset.range k, 1 / ((2 : ℚ) ^ k - 2 ^ l) +
          ∑ b ∈ Finset.range (n - k), 1 / ((2 : ℚ) ^ k - 2 ^ (k + 1 + b)) := by
      let H : ℕ → ℚ := fun l => if l = k then 0 else 1 / ((2 : ℚ) ^ k - 2 ^ l)
      have e1 : ∑ l ∈ (Finset.range (n + 1)).erase k, 1 / ((2 : ℚ) ^ k - 2 ^ l) =
          ∑ l ∈ (Finset.range (n + 1)).erase k, H l :=
        Finset.sum_congr rfl (fun l hl => by simp [H, Finset.ne_of_mem_erase hl])
      rw [e1, Finset.sum_erase _ (by simp [H]),
        show n + 1 = (k + 1) + (n - k) by omega, Finset.sum_range_add, Finset.sum_range_succ]
      have ha : ∑ l ∈ Finset.range k, H l = ∑ l ∈ Finset.range k, 1 / ((2 : ℚ) ^ k - 2 ^ l) :=
        Finset.sum_congr rfl (fun l hl => by
          have := Finset.mem_range.mp hl
          simp [H, show l ≠ k by omega])
      have hb : ∑ b ∈ Finset.range (n - k), H (k + 1 + b) =
          ∑ b ∈ Finset.range (n - k), 1 / ((2 : ℚ) ^ k - 2 ^ (k + 1 + b)) :=
        Finset.sum_congr rfl (fun b _ => by simp [H, show k + 1 + b ≠ k by omega])
      rw [ha, hb]
      simp [H]
    have T3b : (2 : ℚ) ^ k * ∑ l ∈ Finset.range k, 1 / ((2 : ℚ) ^ k - 2 ^ l) =
        ∑ b ∈ Finset.range k, (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := by
      rw [Finset.mul_sum]
      have e1 : ∀ l ∈ Finset.range k, (2 : ℚ) ^ k * (1 / ((2 : ℚ) ^ k - 2 ^ l)) =
          (2 : ℚ) ^ (k - l) / ((2 : ℚ) ^ (k - l) - 1) := by
        intro l hl
        have hlk := Finset.mem_range.mp hl
        rw [show (2 : ℚ) ^ k = 2 ^ l * 2 ^ (k - l) by rw [← pow_add]; congr 1; omega]
        field_simp [h2 l, hpk l hlk] <;> ring
      rw [Finset.sum_congr rfl e1, ← Finset.sum_range_reflect]
      refine Finset.sum_congr rfl (fun b hb => ?_)
      have := Finset.mem_range.mp hb
      rw [show k - (k - 1 - b) = b + 1 by omega]
    have T3c : (2 : ℚ) ^ k * ∑ b ∈ Finset.range (n - k), 1 / ((2 : ℚ) ^ k - 2 ^ (k + 1 + b)) =
        ∑ b ∈ Finset.range (n - k), 1 / (1 - (2 : ℚ) ^ (b + 1)) := by
      rw [Finset.mul_sum]
      refine Finset.sum_congr rfl (fun b _ => ?_)
      rw [show (2 : ℚ) ^ (k + 1 + b) = 2 ^ k * 2 ^ (b + 1) by
        rw [show k + 1 + b = k + (b + 1) by omega, pow_add]]
      have : (2 : ℚ) ^ k - 2 ^ k * 2 ^ (b + 1) = 2 ^ k * (1 - 2 ^ (b + 1)) := by ring
      rw [this]
      field_simp [h2 k, hs1' b] <;> ring
    have T3 : Qc n k * (2 : ℚ) ^ k * ∑ l ∈ (Finset.range (n + 1)).erase k, 1 / ((2 : ℚ) ^ k - 2 ^ l) =
        Qc n k * (∑ b ∈ Finset.range k, (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) +
          ∑ b ∈ Finset.range (n - k), 1 / (1 - (2 : ℚ) ^ (b + 1))) := by
      rw [T3a]
      linear_combination (Qc n k) * T3b + (Qc n k) * T3c
    rw [T0]
    linear_combination hpf - T1 + T2 - T3
  have hclosed := hclosedAll Qc hQc n k hk
  have gauss : ∀ n k : ℕ,
      ∃ z : ℤ, (z : ℚ) = ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
    intro n k
    have hD : ∀ j : ℕ, ((2 : ℚ) ^ (j + 1) - 1) ≠ 0 := by
      intro j
      have h1 : (1 : ℚ) < 2 ^ (j + 1) := one_lt_pow₀ (by norm_num) (by omega)
      exact ne_of_gt (sub_pos.mpr h1)
    have hDk : ∀ k : ℕ, (∏ i ∈ Finset.range k, ((2 : ℚ) ^ (i + 1) - 1)) ≠ 0 := by
      intro k
      exact Finset.prod_ne_zero_iff.mpr (fun i _ => hD i)
    have key : ∀ m j : ℕ,
        (∏ i ∈ Finset.range (j + 1), ((2 : ℚ) ^ (m + 1 - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) =
          (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (m - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) +
          2 ^ (j + 1) *
            ∏ i ∈ Finset.range (j + 1), ((2 : ℚ) ^ (m - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
      intro m j
      simp only [Finset.prod_div_distrib]
      rw [Finset.prod_range_succ' (fun i => (2 : ℚ) ^ (m + 1 - i) - 1)]
      have hshift : ∀ i : ℕ, m + 1 - (i + 1) = m - i := fun i => by omega
      simp only [hshift, Nat.sub_zero]
      rw [Finset.prod_range_succ (fun i => (2 : ℚ) ^ (m - i) - 1),
        Finset.prod_range_succ (fun i => (2 : ℚ) ^ (i + 1) - 1)]
      have hDj := hDk j
      have hj := hD j
      by_cases hjm : j ≤ m
      · have e : (2 : ℚ) ^ (m + 1) = 2 ^ (m - j) * 2 ^ (j + 1) := by
          rw [← pow_add]
          congr 1
          omega
        rw [e]
        field_simp
        ring
      · have hz : (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (m - i) - 1)) = 0 :=
          Finset.prod_eq_zero (i := m) (Finset.mem_range.mpr (by omega)) (by simp)
        rw [hz]
        simp
    have main : ∀ m j : ℕ, ∃ z : ℤ,
        (z : ℚ) = ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (m - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1) := by
      intro m
      induction m with
      | zero =>
        intro j
        cases j with
        | zero => exact ⟨1, by simp⟩
        | succ j =>
          refine ⟨0, ?_⟩
          rw [Finset.prod_eq_zero (i := 0) (by simp) (by simp)]
          simp
      | succ m ih =>
        intro j
        cases j with
        | zero => exact ⟨1, by simp⟩
        | succ j =>
          obtain ⟨a, ha⟩ := ih j
          obtain ⟨b, hb⟩ := ih (j + 1)
          refine ⟨a + 2 ^ (j + 1) * b, ?_⟩
          rw [key, ← ha, ← hb]
          push_cast
          ring
    exact main n k
  have hAcore : ∀ i, i < n → ∃ w : ℤ, (w : ℚ) * ((2 : ℚ) ^ (n + 1 + i - k) - 1) = (M n : ℚ) *
      ∏ j ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - k - j) - 1) / ((2 : ℚ) ^ (j + 1) - 1) := by
    intro i hi
    set h := n / 2 with hh
    set m := 2 * n - k with hm
    have hden : ∀ s : ℕ, (2 : ℚ) ^ (s + 1) - 1 ≠ 0 := by
      intro s
      have : (2 : ℚ) ≤ 2 ^ (s + 1) := by
        calc (2 : ℚ) = 2 ^ 1 := by norm_num
          _ ≤ 2 ^ (s + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
      linarith
    -- M n in ℚ
    have hMq : (M n : ℚ) = ∏ j ∈ Finset.Ioc h n, ((2 : ℚ) ^ j - 1) := by
      rw [hM]
      push_cast
      refine Finset.prod_congr rfl (fun j _ => ?_)
      rw [Nat.cast_sub Nat.one_le_two_pow]
      push_cast
      ring
    -- (2;2)_n = (2;2)_h · M n
    have hsplit : ∏ s ∈ Finset.range n, ((2 : ℚ) ^ (s + 1) - 1) =
        (∏ s ∈ Finset.range h, ((2 : ℚ) ^ (s + 1) - 1)) * ∏ j ∈ Finset.Ioc h n, ((2 : ℚ) ^ j - 1) := by
      have hI : Finset.Ioc h n = Finset.Ico (h + 1) (n + 1) := by
        ext j; simp only [Finset.mem_Ioc, Finset.mem_Ico]; omega
      rw [hI, Finset.prod_Ico_eq_prod_range, show n + 1 - (h + 1) = n - h by omega]
      conv_lhs => rw [show n = h + (n - h) by omega]
      rw [Finset.prod_range_add]
      congr 1
      refine Finset.prod_congr rfl (fun t _ => ?_)
      rw [show h + t + 1 = h + 1 + t by omega]
    set i1 := n - 1 - i with hi1
    have ha : m - i1 = n + 1 + i - k := by omega
    have hnum : ∏ j ∈ Finset.range n, ((2 : ℚ) ^ (m - j) - 1) =
        (∏ j ∈ Finset.range i1, ((2 : ℚ) ^ (m - j) - 1)) * ((2 : ℚ) ^ (m - i1) - 1) *
          ∏ t ∈ Finset.range (n - 1 - i1), ((2 : ℚ) ^ (m - (i1 + 1 + t)) - 1) := by
      conv_lhs => rw [show n = (i1 + 1) + (n - 1 - i1) by omega]
      rw [Finset.prod_range_add, Finset.prod_range_succ]
    have hQh : ∏ s ∈ Finset.range h, ((2 : ℚ) ^ (s + 1) - 1) ≠ 0 :=
      Finset.prod_ne_zero_iff.mpr (fun s _ => hden s)
    have hPM : ∏ j ∈ Finset.Ioc h n, ((2 : ℚ) ^ j - 1) ≠ 0 := by
      refine Finset.prod_ne_zero_iff.mpr (fun j hj => ?_)
      have hj1 := (Finset.mem_Ioc.mp hj).1
      rw [show j = (j - 1) + 1 by omega]
      exact hden _
    rw [Finset.prod_div_distrib, hsplit, hMq, hnum, ha]
    rcases Nat.lt_or_ge i1 h with hlt | hge
    · -- the run above i1 holds h consecutive exponents
      obtain ⟨z0, hz0⟩ := gauss (m - i1 - 1) h
      rw [Finset.prod_div_distrib] at hz0
      have hY : ∏ t ∈ Finset.range (n - 1 - i1), ((2 : ℚ) ^ (m - (i1 + 1 + t)) - 1) =
          (∏ t ∈ Finset.range h, ((2 : ℚ) ^ (m - i1 - 1 - t) - 1)) *
            ∏ t ∈ Finset.range (n - 1 - i1 - h), ((2 : ℚ) ^ (m - (i1 + 1 + (h + t))) - 1) := by
        conv_lhs => rw [show n - 1 - i1 = h + (n - 1 - i1 - h) by omega]
        rw [Finset.prod_range_add]
        congr 1
        refine Finset.prod_congr rfl (fun t _ => ?_)
        rw [show m - (i1 + 1 + t) = m - i1 - 1 - t by omega]
      refine ⟨z0 * (∏ j ∈ Finset.range i1, ((2 : ℤ) ^ (m - j) - 1)) *
        ∏ t ∈ Finset.range (n - 1 - i1 - h), ((2 : ℤ) ^ (m - (i1 + 1 + (h + t))) - 1), ?_⟩
      push_cast
      rw [hz0, hY]
      field_simp
    · -- the run below i1 holds h consecutive exponents
      obtain ⟨z0, hz0⟩ := gauss m h
      rw [Finset.prod_div_distrib] at hz0
      have hX : ∏ j ∈ Finset.range i1, ((2 : ℚ) ^ (m - j) - 1) =
          (∏ j ∈ Finset.range h, ((2 : ℚ) ^ (m - j) - 1)) *
            ∏ t ∈ Finset.range (i1 - h), ((2 : ℚ) ^ (m - (h + t)) - 1) := by
        conv_lhs => rw [show i1 = h + (i1 - h) by omega]
        rw [Finset.prod_range_add]
      refine ⟨z0 * (∏ t ∈ Finset.range (i1 - h), ((2 : ℤ) ^ (m - (h + t)) - 1)) *
        ∏ t ∈ Finset.range (n - 1 - i1), ((2 : ℤ) ^ (m - (i1 + 1 + t)) - 1), ?_⟩
      push_cast
      rw [hz0, hX]
      field_simp
  -- the cyclotomic-count ingredient: removing one factor from Π_{t=n-k+1}^{2n-k}(2^t - 1) leaves a run
  -- of ⌊n/2⌋ consecutive exponents, whose product over (2;2)_{⌊n/2⌋} is a Gaussian binomial
  have hA : ∀ i < n, ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (k * (k - 1) / 2) =
      (M n : ℚ) * Qc n k * (1 / (1 - (2 : ℚ) ^ (n + 1 + i - k))) := by
    intro i hi
    obtain ⟨w, hw⟩ := hAcore i hi
    obtain ⟨g1, hg1⟩ := gauss n k
    have hne : (1 : ℚ) - 2 ^ (n + 1 + i - k) ≠ 0 := by
      have : (2 : ℚ) ≤ 2 ^ (n + 1 + i - k) := by
        calc (2 : ℚ) = 2 ^ 1 := by norm_num
          _ ≤ 2 ^ (n + 1 + i - k) := pow_le_pow_right₀ (by norm_num) (by omega)
      linarith
    refine ⟨-((-1) ^ k * g1 * w), ?_⟩
    rw [hQc]
    simp only []
    rw [← hg1]
    push_cast
    field_simp
    linear_combination (g1 : ℚ) * hw
  -- proved: 2^b - 1 divides M n for 1 ≤ b ≤ n (b has a multiple in (n/2, n])
  have hdvd : ∀ b : ℕ, 1 ≤ b → b ≤ n → ∃ R : ℕ, M n = (2 ^ b - 1) * R := by
    intro b hb1 hbn
    have h1 : b * (n / b) ≤ n := Nat.mul_div_le n b
    have h2 : n < b * (n / b) + b := by
      have := Nat.lt_mul_div_succ n (show 0 < b by omega)
      rw [Nat.mul_succ] at this
      exact this
    have h3 : b ≤ b * (n / b) := Nat.le_mul_of_pos_right b (Nat.div_pos hbn (by omega))
    have hmem : b * (n / b) ∈ Finset.Ioc (n / 2) n := Finset.mem_Ioc.mpr ⟨by omega, h1⟩
    have hd1 : 2 ^ b - 1 ∣ 2 ^ (b * (n / b)) - 1 := by
      have : 2 ^ b - 1 ∣ (2 ^ b) ^ (n / b) - 1 ^ (n / b) := by
        first
          | exact Nat.sub_dvd_pow_sub_pow _ _ _
          | exact nat_sub_dvd_pow_sub_pow _ _ _
      rwa [one_pow, ← pow_mul] at this
    have hd2 : 2 ^ (b * (n / b)) - 1 ∣ ∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1) :=
      Finset.dvd_prod_of_mem (fun m => 2 ^ m - 1) hmem
    obtain ⟨R, hR⟩ := dvd_trans hd1 hd2
    exact ⟨R, by rw [hM]; exact hR⟩
  have hcast : ∀ b : ℕ, (((2 ^ b - 1 : ℕ)) : ℚ) = (2 : ℚ) ^ b - 1 := by
    intro b
    rw [Nat.cast_sub (Nat.one_le_two_pow)]
    push_cast
    ring
  have hne : ∀ b : ℕ, (2 : ℚ) ^ (b + 1) - 1 ≠ 0 := by
    intro b
    have : (2 : ℚ) ≤ 2 ^ (b + 1) := by
      calc (2 : ℚ) = 2 ^ 1 := by norm_num
        _ ≤ 2 ^ (b + 1) := pow_le_pow_right₀ (by norm_num) (by omega)
    linarith
  let P : ℚ → Prop := fun x => ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (k * (k - 1) / 2) = x
  have hadd : ∀ x y : ℚ, P x → P y → P (x + y) := fun x y ⟨a, ha⟩ ⟨b, hb⟩ =>
    ⟨a + b, by push_cast; rw [add_mul, ha, hb]⟩
  have hsub : ∀ x y : ℚ, P x → P y → P (x - y) := fun x y ⟨a, ha⟩ ⟨b, hb⟩ =>
    ⟨a - b, by push_cast; rw [sub_mul, ha, hb]⟩
  have hsum : ∀ (s : Finset ℕ) (f : ℕ → ℚ), (∀ i ∈ s, P (f i)) → P (∑ i ∈ s, f i) :=
    fun s f h => Finset.sum_induction _ P hadd ⟨0, by simp⟩ h
  obtain ⟨zk, hzk⟩ := hQcint k hk
  show P _
  rw [hclosed]
  have eq : (M n : ℚ) * (Qc n k * (∑ i ∈ Finset.range n, 1 / (1 - (2 : ℚ) ^ (n + 1 + i - k)) -
          ∑ b ∈ Finset.range k, (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) -
          ∑ b ∈ Finset.range (n - k), 1 / (1 - (2 : ℚ) ^ (b + 1))) +
        ∑ b ∈ Finset.range (n - k), Qc n (k + b + 1) * (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1)) =
      (M n : ℚ) * Qc n k * ∑ i ∈ Finset.range n, 1 / (1 - (2 : ℚ) ^ (n + 1 + i - k)) -
        (M n : ℚ) * Qc n k * ∑ b ∈ Finset.range k, (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) -
        (M n : ℚ) * Qc n k * ∑ b ∈ Finset.range (n - k), 1 / (1 - (2 : ℚ) ^ (b + 1)) +
        (M n : ℚ) * ∑ b ∈ Finset.range (n - k), Qc n (k + b + 1) * (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := by
    ring
  rw [eq]
  refine hadd _ _ (hsub _ _ (hsub _ _ ?_ ?_) ?_) ?_
  · rw [Finset.mul_sum]
    exact hsum _ _ (fun i hi => hA i (Finset.mem_range.mp hi))
  · rw [Finset.mul_sum]
    refine hsum _ _ (fun b hb => ?_)
    have hbk := Finset.mem_range.mp hb
    obtain ⟨R, hR⟩ := hdvd (b + 1) (by omega) (by omega)
    refine ⟨zk * 2 ^ (b + 1) * R, ?_⟩
    rw [hR, ← hzk, Nat.cast_mul, hcast]
    push_cast
    field_simp [hne b]
  · rw [Finset.mul_sum]
    refine hsum _ _ (fun b hb => ?_)
    have hbk := Finset.mem_range.mp hb
    obtain ⟨R, hR⟩ := hdvd (b + 1) (by omega) (by omega)
    refine ⟨-(zk * R), ?_⟩
    have hne' : (1 : ℚ) - 2 ^ (b + 1) ≠ 0 := fun h => hne b (by linarith)
    rw [hR, ← hzk, Nat.cast_mul, hcast]
    push_cast
    field_simp [hne b, hne']
    ring
  · rw [Finset.mul_sum]
    refine hsum _ _ (fun b hb => ?_)
    have hbk := Finset.mem_range.mp hb
    obtain ⟨R, hR⟩ := hdvd (b + 1) (by omega) (by omega)
    obtain ⟨z', hz'⟩ := hQcint (k + b + 1) (by omega)
    have hT : k * (k - 1) / 2 ≤ (k + b + 1) * (k + b + 1 - 1) / 2 :=
      Nat.div_le_div_right (Nat.mul_le_mul (by omega) (by omega))
    have hpow : (2 : ℚ) ^ ((k + b + 1) * (k + b + 1 - 1) / 2) =
        (2 : ℚ) ^ ((k + b + 1) * (k + b + 1 - 1) / 2 - k * (k - 1) / 2) * (2 : ℚ) ^ (k * (k - 1) / 2) := by
      rw [← pow_add, Nat.sub_add_cancel hT]
    refine ⟨R * z' * 2 ^ (b + 1) * 2 ^ ((k + b + 1) * (k + b + 1 - 1) / 2 - k * (k - 1) / 2), ?_⟩
    rw [hR, ← hz', Nat.cast_mul, hcast, hpow]
    push_cast
    field_simp [hne b]
