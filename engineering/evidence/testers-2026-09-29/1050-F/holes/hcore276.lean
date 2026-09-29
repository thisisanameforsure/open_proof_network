import Mathlib

theorem hcore_hole : ∀ (Qc : ℕ → ℕ → ℚ),
    (Qc = fun (n k : ℕ) =>
        ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
            ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
          ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) →
    ∀ (n k : ℕ), k ≤ n →
      ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (k * (k - 1) / 2) =
        (∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ m - 1)) *
          ∑ j ∈ Finset.range (k + (1 : ℕ)), Qc n j / ((2 : ℚ) ^ (k - j) - (1 : ℚ)) := by
  intro Qc hQc n k hk
  -- Gaussian binomial integrality at q = 2: the block below is t0929-1's (graph PR #276 / annex on h3), unchanged
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
  have pint : ∀ (Qc : ℕ → ℕ → ℚ),
    (Qc = fun (n k : ℕ) =>
        ((-1 : ℚ) ^ k * (2 : ℚ) ^ (k * (k - (1 : ℕ)) / (2 : ℕ)) *
            ∏ i ∈ Finset.range k, ((2 : ℚ) ^ (n - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) *
          ∏ i ∈ Finset.range n, ((2 : ℚ) ^ ((2 : ℕ) * n - k - i) - (1 : ℚ)) / ((2 : ℚ) ^ (i + (1 : ℕ)) - (1 : ℚ))) →
      ∀ (n : ℕ), (∀ k ≤ n, ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (k * (k - 1) / 2) = Qc n k) →
        ∀ k ≤ n, ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (k * (k - 1) / 2) =
          ((∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1) : ℕ) : ℚ) *
            ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1) := by
    intro Qc hQc n hQcint k hk
    have bn_odd : ∀ (n : ℕ),
        Odd (∏ t ∈ Finset.range (2 * n), ((2 : ℤ) ^ (t + 1) - 1)) := by
      intro n
      apply Finset.prod_induction _ Odd (fun a b ha hb => ha.mul hb) odd_one
      intro t _
      exact ⟨2 ^ t - 1, by ring⟩
    have bn_dvd : ∀ (n t : ℕ) (h1 : 1 ≤ t) (h2 : t ≤ 2 * n),
        ((2 : ℤ) ^ t - 1) ∣ ∏ s ∈ Finset.range (2 * n), ((2 : ℤ) ^ (s + 1) - 1) := by
      intro n t h1 h2
      have hm : t - 1 ∈ Finset.range (2 * n) := Finset.mem_range.2 (by omega)
      have := Finset.dvd_prod_of_mem (fun s => ((2 : ℤ) ^ (s + 1) - 1)) hm
      simpa [Nat.sub_add_cancel h1] using this
    have good_basic : ∀ (n c e t : ℕ) (g : ℤ) (he : c ≤ e) (h1 : 1 ≤ t) (h2 : t ≤ 2 * n),
        ∃ A : ℤ, ((∏ s ∈ Finset.range (2 * n), ((2 : ℤ) ^ (s + 1) - 1) : ℤ) : ℚ) * ((2 : ℚ) ^ e * g / ((2 : ℚ) ^ t - 1)) =
          (2 : ℚ) ^ c * A := by
      intro n c e t g he h1 h2
      obtain ⟨Q, hQ⟩ := bn_dvd n t h1 h2
      refine ⟨2 ^ (e - c) * g * Q, ?_⟩
      have hne : ((2 : ℚ) ^ t - 1) ≠ 0 := by
        have : (1 : ℚ) < 2 ^ t := one_lt_pow₀ (by norm_num) (by omega)
        linarith
      rw [hQ]
      push_cast
      have hp : (2 : ℚ) ^ e = 2 ^ c * 2 ^ (e - c) := by rw [← pow_add, Nat.add_sub_cancel' he]
      rw [hp]
      field_simp
    have lagrange_fp : ∀ (s : Finset ℕ) (x : ℕ → ℚ) (hx : Set.InjOn x s) (r : ℕ → ℚ) (N : Polynomial ℚ)
        (hN : N.natDegree < s.card)
        (hr : ∀ j ∈ s, r j * ∏ i ∈ s.erase j, (x j - x i) = N.eval (x j)),
        N = ∑ j ∈ s, Polynomial.C (r j) * ∏ i ∈ s.erase j, (Polynomial.X - Polynomial.C (x i)) := by
      intro s x hx r N hN hr
      have hdeg : (∑ j ∈ s, Polynomial.C (r j) * ∏ i ∈ s.erase j, (Polynomial.X - Polynomial.C (x i)) - N).natDegree < s.card := by
        have hs : 0 < s.card := by
          rcases Nat.eq_zero_or_pos s.card with h | h
          · omega
          · exact h
        refine lt_of_le_of_lt (Polynomial.natDegree_sub_le _ _) (max_lt ?_ hN)
        refine lt_of_le_of_lt (Polynomial.natDegree_sum_le_of_forall_le s _ (n := s.card - 1) ?_) (by omega)
        intro j hj
        refine (Polynomial.natDegree_C_mul_le _ _).trans ?_
        rw [Polynomial.natDegree_finsetProd_X_sub_C_eq_card, Finset.card_erase_of_mem hj]
      have hzero : ∑ j ∈ s, Polynomial.C (r j) * ∏ i ∈ s.erase j, (Polynomial.X - Polynomial.C (x i)) - N = 0 := by
        apply Polynomial.eq_zero_of_natDegree_lt_card_of_eval_eq_zero' _ (s.image x)
        · intro y hy
          obtain ⟨i, hi, rfl⟩ := Finset.mem_image.1 hy
          rw [Polynomial.eval_sub, Polynomial.eval_finsetSum, Finset.sum_eq_single i]
          · rw [Polynomial.eval_mul, Polynomial.eval_C, Polynomial.eval_prod]
            simp only [Polynomial.eval_sub, Polynomial.eval_X, Polynomial.eval_C]
            rw [hr i hi, sub_self]
          · intro j hj hji
            rw [Polynomial.eval_mul, Polynomial.eval_prod]
            apply mul_eq_zero_of_right
            apply Finset.prod_eq_zero (i := i)
            · exact Finset.mem_erase.2 ⟨Ne.symm hji, hi⟩
            · simp
          · intro h; exact absurd hi h
        · rw [Finset.card_image_of_injOn hx]; exact hdeg
      exact (sub_eq_zero.1 hzero).symm
    have deriv_eval : ∀ (s : Finset ℕ) (x : ℕ → ℚ) (hx : Set.InjOn x s) (r : ℕ → ℚ) (k : ℕ) (hk : k ∈ s),
        (Polynomial.derivative (∑ j ∈ s, Polynomial.C (r j) * ∏ i ∈ s.erase j, (Polynomial.X - Polynomial.C (x i)))).eval (x k) =
          (∏ i ∈ s.erase k, (x k - x i)) *
            (∑ j ∈ s.erase k, r j / (x k - x j) + r k * ∑ i ∈ s.erase k, 1 / (x k - x i)) := by
      intro s x hx r k hk
      have hne : ∀ i ∈ s.erase k, x k - x i ≠ 0 := by
        intro i hi h
        have hik := (Finset.mem_erase.1 hi)
        exact hik.1 (hx hik.2 hk (sub_eq_zero.1 h).symm)
      have hD : ∀ a ∈ s.erase k, ∏ b ∈ (s.erase k).erase a, (x k - x b) = (∏ i ∈ s.erase k, (x k - x i)) / (x k - x a) := by
        intro a ha
        rw [eq_div_iff (hne a ha), mul_comm]
        exact Finset.mul_prod_erase (s.erase k) (fun b => x k - x b) ha
      rw [Polynomial.derivative_sum, Polynomial.eval_finsetSum, ← Finset.add_sum_erase _ _ hk]
      have hterm : ∀ j ∈ s.erase k, (Polynomial.derivative (Polynomial.C (r j) * ∏ i ∈ s.erase j, (Polynomial.X - Polynomial.C (x i)))).eval (x k) =
          r j * ((∏ i ∈ s.erase k, (x k - x i)) / (x k - x j)) := by
        intro j hj
        rw [Polynomial.derivative_C_mul, Polynomial.eval_mul, Polynomial.eval_C, Polynomial.derivative_prod_finset, Polynomial.eval_finsetSum]
        congr 1
        have hkj : k ∈ s.erase j := Finset.mem_erase.2 ⟨fun h => (Finset.mem_erase.1 hj).1 h.symm, hk⟩
        rw [Finset.sum_eq_single k]
        · rw [Polynomial.derivative_X_sub_C, mul_one, Polynomial.eval_prod]
          simp only [Polynomial.eval_sub, Polynomial.eval_X, Polynomial.eval_C]
          rw [Finset.erase_right_comm]
          exact hD j hj
        · intro a ha hak
          rw [Polynomial.eval_mul, Polynomial.eval_prod]
          apply mul_eq_zero_of_left
          apply Finset.prod_eq_zero (i := k)
          · exact Finset.mem_erase.2 ⟨fun h => hak h.symm, hkj⟩
          · simp
        · intro h; exact absurd hkj h
      rw [Finset.sum_congr rfl hterm]
      rw [Polynomial.derivative_C_mul, Polynomial.eval_mul, Polynomial.eval_C, Polynomial.derivative_prod_finset, Polynomial.eval_finsetSum]
      have hself : ∀ a ∈ s.erase k, ((∏ b ∈ (s.erase k).erase a, (Polynomial.X - Polynomial.C (x b))) * Polynomial.derivative (Polynomial.X - Polynomial.C (x a))).eval (x k) =
          (∏ i ∈ s.erase k, (x k - x i)) / (x k - x a) := by
        intro a ha
        rw [Polynomial.derivative_X_sub_C, mul_one, Polynomial.eval_prod]
        simp only [Polynomial.eval_sub, Polynomial.eval_X, Polynomial.eval_C]
        exact hD a ha
      rw [Finset.sum_congr rfl hself]
      rw [mul_add, add_comm]
      congr 1
      · rw [Finset.mul_sum]
        apply Finset.sum_congr rfl
        intro j _
        ring
      · rw [Finset.mul_sum, Finset.mul_sum, Finset.mul_sum]
        apply Finset.sum_congr rfl
        intro j _
        ring
    have nprod_deriv : ∀ (T : Finset ℕ) (y : ℕ → ℚ) (z : ℚ) (hz : ∀ m ∈ T, z - y m ≠ 0),
        (Polynomial.derivative (∏ m ∈ T, (Polynomial.X - Polynomial.C (y m)))).eval z = (∏ m ∈ T, (z - y m)) * ∑ m ∈ T, 1 / (z - y m) := by
      intro T y z hz
      rw [Polynomial.derivative_prod_finset, Polynomial.eval_finsetSum, Finset.mul_sum]
      apply Finset.sum_congr rfl
      intro m hm
      rw [Polynomial.derivative_X_sub_C, mul_one, Polynomial.eval_prod]
      simp only [Polynomial.eval_sub, Polynomial.eval_X, Polynomial.eval_C]
      rw [← Finset.mul_prod_erase T (fun b => z - y b) hm]
      field_simp [hz m hm]
    have star : ∀ (n k : ℕ) (hk : k ≤ n) (a : ℕ → ℚ)
        (ha : ∀ j ≤ n, a j * 2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
          ∏ m ∈ Finset.Ico (n + 1) (2 * n + 1), ((2 : ℚ) ^ j - 2 ^ m)),
        ∑ j ∈ (Finset.range (n + 1)).erase k, a j * 2 ^ j / ((2 : ℚ) ^ k - 2 ^ j) =
          a k * 2 ^ k * (∑ m ∈ Finset.Ico (n + 1) (2 * n + 1), 1 / ((2 : ℚ) ^ k - 2 ^ m) -
            ∑ i ∈ (Finset.range (n + 1)).erase k, 1 / ((2 : ℚ) ^ k - 2 ^ i)) := by
      intro n k hk a ha
      have hinj : ∀ a b : ℕ, (2 : ℚ) ^ a = 2 ^ b → a = b := by
        intro a b h
        have h' : (2 : ℕ) ^ a = 2 ^ b := by exact_mod_cast h
        exact Nat.pow_right_injective (le_refl 2) h'
      have hx : Set.InjOn (fun i : ℕ => (2 : ℚ) ^ i) (Finset.range (n + 1) : Set ℕ) :=
        fun a _ b _ h => hinj a b h
      have hkmem : k ∈ Finset.range (n + 1) := Finset.mem_range.2 (by omega)
      have hN : (∏ m ∈ Finset.Ico (n + 1) (2 * n + 1), (Polynomial.X - Polynomial.C ((2 : ℚ) ^ m))).natDegree < (Finset.range (n + 1)).card := by
        rw [Polynomial.natDegree_finsetProd_X_sub_C_eq_card, Nat.card_Ico, Finset.card_range]
        omega
      have hr : ∀ j ∈ Finset.range (n + 1), a j * 2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
          (∏ m ∈ Finset.Ico (n + 1) (2 * n + 1), (Polynomial.X - Polynomial.C ((2 : ℚ) ^ m))).eval ((2 : ℚ) ^ j) := by
        intro j hj
        rw [ha j (by simp at hj; omega), Polynomial.eval_prod]
        simp only [Polynomial.eval_sub, Polynomial.eval_X, Polynomial.eval_C]
      have hL := lagrange_fp (Finset.range (n + 1)) (fun i => (2 : ℚ) ^ i) hx (fun j => a j * 2 ^ j) _ hN hr
      have hdiff := congrArg (fun p => (Polynomial.derivative p).eval ((2 : ℚ) ^ k)) hL
      simp only at hdiff
      rw [deriv_eval _ _ hx _ k hkmem] at hdiff
      have hzm : ∀ m ∈ Finset.Ico (n + 1) (2 * n + 1), (2 : ℚ) ^ k - 2 ^ m ≠ 0 := by
        intro m hm h
        have := hinj k m (sub_eq_zero.1 h)
        simp at hm; omega
      rw [nprod_deriv _ _ _ hzm] at hdiff
      have hDne : (∏ i ∈ (Finset.range (n + 1)).erase k, ((2 : ℚ) ^ k - 2 ^ i)) ≠ 0 := by
        rw [Finset.prod_ne_zero_iff]
        intro i hi h
        have := hinj k i (sub_eq_zero.1 h)
        exact (Finset.mem_erase.1 hi).1 this.symm
      rw [← ha k hk] at hdiff
      -- hdiff : a k 2^k D * S_m = D * (sum_{j≠k} r_j/(x_k-x_j) + r_k * S_i)
      have key : (∏ i ∈ (Finset.range (n + 1)).erase k, ((2 : ℚ) ^ k - 2 ^ i)) *
          (∑ j ∈ (Finset.range (n + 1)).erase k, a j * 2 ^ j / ((2 : ℚ) ^ k - 2 ^ j)) =
          (∏ i ∈ (Finset.range (n + 1)).erase k, ((2 : ℚ) ^ k - 2 ^ i)) *
          (a k * 2 ^ k * (∑ m ∈ Finset.Ico (n + 1) (2 * n + 1), 1 / ((2 : ℚ) ^ k - 2 ^ m) -
            ∑ i ∈ (Finset.range (n + 1)).erase k, 1 / ((2 : ℚ) ^ k - 2 ^ i))) := by
        linear_combination -hdiff
      exact mul_left_cancel₀ hDne key
    have two_adic_core : ∀ (a : ℕ → ℚ) (n k : ℕ) (hk : k ≤ n)
        (hform : ∀ j ≤ n, ∃ g : ℤ, a j = (-1) ^ j * 2 ^ (j * (j - 1) / 2) * g)
        (ha : ∀ j ≤ n, a j * 2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
          ∏ m ∈ Finset.Ico (n + 1) (2 * n + 1), ((2 : ℚ) ^ j - 2 ^ m)),
        ∃ A : ℤ, ((∏ s ∈ Finset.range (2 * n), ((2 : ℤ) ^ (s + 1) - 1) : ℤ) : ℚ) *
          (∑ j ∈ Finset.range (k + 1), a j / ((2 : ℚ) ^ (k - j) - 1)) = (2 : ℚ) ^ (k * (k - 1) / 2) * A := by
      intro a n k hk hform ha
      set Bn : ℤ := ∏ s ∈ Finset.range (2 * n), ((2 : ℤ) ^ (s + 1) - 1) with hBn
      set c := k * (k - 1) / 2 with hc
      -- "good": Bn * q is 2^c times an integer
      have gadd : ∀ p q : ℚ, (∃ A : ℤ, (Bn : ℚ) * p = 2 ^ c * A) → (∃ A : ℤ, (Bn : ℚ) * q = 2 ^ c * A) →
          ∃ A : ℤ, (Bn : ℚ) * (p + q) = 2 ^ c * A := by
        rintro p q ⟨A, hA⟩ ⟨B, hB⟩
        exact ⟨A + B, by push_cast; rw [mul_add, hA, hB]; ring⟩
      have gneg : ∀ p : ℚ, (∃ A : ℤ, (Bn : ℚ) * p = 2 ^ c * A) → ∃ A : ℤ, (Bn : ℚ) * (-p) = 2 ^ c * A := by
        rintro p ⟨A, hA⟩
        exact ⟨-A, by push_cast; rw [mul_neg, hA]; ring⟩
      have gsum : ∀ (s : Finset ℕ) (f : ℕ → ℚ), (∀ i ∈ s, ∃ A : ℤ, (Bn : ℚ) * f i = 2 ^ c * A) →
          ∃ A : ℤ, (Bn : ℚ) * ∑ i ∈ s, f i = 2 ^ c * A := by
        intro s f hf
        exact Finset.sum_induction f (fun q => ∃ A : ℤ, (Bn : ℚ) * q = 2 ^ c * A) gadd ⟨0, by simp⟩ hf
      have gbasic : ∀ (e t : ℕ) (g : ℤ), c ≤ e → 1 ≤ t → t ≤ 2 * n →
          ∃ A : ℤ, (Bn : ℚ) * ((2 : ℚ) ^ e * g / ((2 : ℚ) ^ t - 1)) = 2 ^ c * A :=
        fun e t g he h1 h2 => good_basic n c e t g he h1 h2
      -- two small identities for quotients of powers of 2
      have qlow : ∀ i m : ℕ, i < m → (2 : ℚ) ^ i / (2 ^ i - 2 ^ m) = -1 / (2 ^ (m - i) - 1) := by
        intro i m him
        have hm : (2 : ℚ) ^ m = 2 ^ i * 2 ^ (m - i) := by rw [← pow_add, Nat.add_sub_cancel' him.le]
        have h1 : (2 : ℚ) ^ (m - i) - 1 ≠ 0 := by
          have : (1 : ℚ) < 2 ^ (m - i) := one_lt_pow₀ (by norm_num) (by omega)
          linarith
        have h2 : (2 : ℚ) ^ i - 2 ^ m ≠ 0 := by
          rw [hm]
          have : (0 : ℚ) < 2 ^ i := by positivity
          intro h
          apply h1
          have : (2 : ℚ) ^ i * (1 - 2 ^ (m - i)) = 0 := by linarith
          rcases mul_eq_zero.1 this with h' | h'
          · linarith
          · linarith
        rw [div_eq_div_iff h2 h1, hm]
        ring
      have qhigh : ∀ i m : ℕ, i < m → (2 : ℚ) ^ m / (2 ^ m - 2 ^ i) = 2 ^ (m - i) / (2 ^ (m - i) - 1) := by
        intro i m him
        have hm : (2 : ℚ) ^ m = 2 ^ i * 2 ^ (m - i) := by rw [← pow_add, Nat.add_sub_cancel' him.le]
        have h1 : (2 : ℚ) ^ (m - i) - 1 ≠ 0 := by
          have : (1 : ℚ) < 2 ^ (m - i) := one_lt_pow₀ (by norm_num) (by omega)
          linarith
        have hi : (2 : ℚ) ^ i ≠ 0 := by positivity
        rw [hm]
        rw [show (2 : ℚ) ^ i * 2 ^ (m - i) - 2 ^ i = 2 ^ i * (2 ^ (m - i) - 1) by ring]
        field_simp
      have qmid : ∀ j m : ℕ, j < m → (2 : ℚ) ^ j / (2 ^ m - 2 ^ j) = 1 / (2 ^ (m - j) - 1) := by
        intro j m hjm
        have hm : (2 : ℚ) ^ m = 2 ^ j * 2 ^ (m - j) := by rw [← pow_add, Nat.add_sub_cancel' hjm.le]
        have h1 : (2 : ℚ) ^ (m - j) - 1 ≠ 0 := by
          have : (1 : ℚ) < 2 ^ (m - j) := one_lt_pow₀ (by norm_num) (by omega)
          linarith
        have hj : (2 : ℚ) ^ j ≠ 0 := by positivity
        rw [hm, show (2 : ℚ) ^ j * 2 ^ (m - j) - 2 ^ j = 2 ^ j * (2 ^ (m - j) - 1) by ring]
        field_simp
      obtain ⟨gk, hgk⟩ := hform k hk
      have hp : ∑ j ∈ Finset.range (k + 1), a j / ((2 : ℚ) ^ (k - j) - 1) =
          ∑ j ∈ Finset.range k, a j * 2 ^ j / ((2 : ℚ) ^ k - 2 ^ j) := by
        rw [Finset.sum_range_succ, Nat.sub_self, pow_zero, sub_self, div_zero, add_zero]
        apply Finset.sum_congr rfl
        intro j hj
        rw [Finset.mem_range] at hj
        rw [mul_div_assoc, qmid j k hj, mul_one_div]
      have hsplit : (Finset.range (n + 1)).erase k = Finset.range k ∪ Finset.Ioc k n := by
        ext i
        simp only [Finset.mem_erase, Finset.mem_range, Finset.mem_union, Finset.mem_Ioc]
        omega
      have hdisj : Disjoint (Finset.range k) (Finset.Ioc k n) := by
        rw [Finset.disjoint_left]
        intro i hi hi'
        simp only [Finset.mem_range, Finset.mem_Ioc] at hi hi'
        omega
      have hstar := star n k hk a ha
      have hL : ∑ j ∈ (Finset.range (n + 1)).erase k, a j * 2 ^ j / ((2 : ℚ) ^ k - 2 ^ j) =
          ∑ j ∈ Finset.range k, a j * 2 ^ j / ((2 : ℚ) ^ k - 2 ^ j) + ∑ j ∈ Finset.Ioc k n, a j * 2 ^ j / ((2 : ℚ) ^ k - 2 ^ j) := by
        rw [hsplit, Finset.sum_union hdisj]
      have e1 : ∑ m ∈ Finset.Ico (n + 1) (2 * n + 1), a k * 2 ^ k * (1 / ((2 : ℚ) ^ k - 2 ^ m)) =
          a k * 2 ^ k * ∑ m ∈ Finset.Ico (n + 1) (2 * n + 1), 1 / ((2 : ℚ) ^ k - 2 ^ m) := (Finset.mul_sum _ _ _).symm
      have e2 : ∑ i ∈ (Finset.range (n + 1)).erase k, a k * 2 ^ k * (1 / ((2 : ℚ) ^ k - 2 ^ i)) =
          a k * 2 ^ k * ∑ i ∈ (Finset.range (n + 1)).erase k, 1 / ((2 : ℚ) ^ k - 2 ^ i) := (Finset.mul_sum _ _ _).symm
      have hlow : ∑ j ∈ Finset.range k, a j * 2 ^ j / ((2 : ℚ) ^ k - 2 ^ j) =
          (∑ m ∈ Finset.Ico (n + 1) (2 * n + 1), a k * 2 ^ k * (1 / ((2 : ℚ) ^ k - 2 ^ m))) +
          -(∑ i ∈ (Finset.range (n + 1)).erase k, a k * 2 ^ k * (1 / ((2 : ℚ) ^ k - 2 ^ i))) +
          -(∑ j ∈ Finset.Ioc k n, a j * 2 ^ j / ((2 : ℚ) ^ k - 2 ^ j)) := by
        linear_combination hstar - hL - e1 + e2
      -- the term shapes
      have Tlow : ∀ m : ℕ, k < m → a k * 2 ^ k * (1 / ((2 : ℚ) ^ k - 2 ^ m)) =
          (2 : ℚ) ^ c * ((-((-1) ^ k * gk) : ℤ) : ℚ) / (2 ^ (m - k) - 1) := by
        intro m hkm
        have h' : a k * 2 ^ k * (1 / ((2 : ℚ) ^ k - 2 ^ m)) = (-1) ^ k * 2 ^ c * gk * (2 ^ k / (2 ^ k - 2 ^ m)) := by
          rw [hgk]; ring
        rw [h', qlow k m hkm]
        push_cast
        ring
      have Thigh : ∀ i : ℕ, i < k → a k * 2 ^ k * (1 / ((2 : ℚ) ^ k - 2 ^ i)) =
          (2 : ℚ) ^ (c + (k - i)) * (((-1) ^ k * gk : ℤ) : ℚ) / (2 ^ (k - i) - 1) := by
        intro i hik
        have h' : a k * 2 ^ k * (1 / ((2 : ℚ) ^ k - 2 ^ i)) = (-1) ^ k * 2 ^ c * gk * (2 ^ k / (2 ^ k - 2 ^ i)) := by
          rw [hgk]; ring
        rw [h', qhigh i k hik, pow_add]
        push_cast
        ring
      rw [hp, hlow]
      refine gadd _ _ (gadd _ _ ?_ (gneg _ ?_)) (gneg _ ?_)
      · apply gsum
        intro m hm
        simp only [Finset.mem_Ico] at hm
        rw [Tlow m (by omega)]
        exact gbasic c (m - k) _ le_rfl (by omega) (by omega)
      · apply gsum
        intro i hi
        simp only [Finset.mem_erase, Finset.mem_range] at hi
        rcases Nat.lt_or_gt_of_ne hi.1 with hik | hik
        · rw [Thigh i hik]
          exact gbasic (c + (k - i)) (k - i) _ (by omega) (by omega) (by omega)
        · rw [Tlow i hik]
          exact gbasic c (i - k) _ le_rfl (by omega) (by omega)
      · apply gsum
        intro j hj
        simp only [Finset.mem_Ioc] at hj
        obtain ⟨gj, hgj⟩ := hform j hj.2
        have hjk : k < j := hj.1
        have hsw : (2 : ℚ) ^ j / (2 ^ k - 2 ^ j) = -(2 ^ j / (2 ^ j - 2 ^ k)) := by
          rw [← div_neg, neg_sub]
        have hT : a j * 2 ^ j / ((2 : ℚ) ^ k - 2 ^ j) =
            (2 : ℚ) ^ (j * (j - 1) / 2 + (j - k)) * ((-((-1) ^ j * gj) : ℤ) : ℚ) / (2 ^ (j - k) - 1) := by
          rw [mul_div_assoc, hsw, qhigh k j hjk, hgj, pow_add]
          push_cast
          ring
        rw [hT]
        have hce : c ≤ j * (j - 1) / 2 + (j - k) := by
          have : k * (k - 1) / 2 ≤ j * (j - 1) / 2 :=
            Nat.div_le_div_right (Nat.mul_le_mul hjk.le (Nat.sub_le_sub_right hjk.le 1))
          omega
        exact gbasic _ (j - k) _ hce (by omega) (by omega)
    have residue : ∀ (n j : ℕ) (hj : j ≤ n),
        ((-1 : ℚ) ^ j * (2 : ℚ) ^ (j * (j - 1) / 2) *
            ∏ i ∈ Finset.range j, ((2 : ℚ) ^ (n - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) *
          (∏ i ∈ Finset.range n, ((2 : ℚ) ^ (2 * n - j - i) - 1) / ((2 : ℚ) ^ (i + 1) - 1)) * 2 ^ j *
          ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
        ∏ m ∈ Finset.Ico (n + 1) (2 * n + 1), ((2 : ℚ) ^ j - 2 ^ m) := by
      intro n j hj
      obtain ⟨r, rfl⟩ : ∃ r, n = r + j := ⟨n - j, by omega⟩
      -- q-factorial P b = ∏_{i<b} (2^(i+1) - 1), and the shifted block U r b = ∏_{s<b} (2^(r+1+s) - 1)
      have hPne : ∀ b : ℕ, (∏ i ∈ Finset.range b, ((2 : ℚ) ^ (i + 1) - 1)) ≠ 0 := by
        intro b
        rw [Finset.prod_ne_zero_iff]
        intro i _
        have : (1 : ℚ) < 2 ^ (i + 1) := one_lt_pow₀ (by norm_num) (by omega)
        linarith
      have hA : (∏ i ∈ Finset.range j, ((2 : ℚ) ^ (r + j - i) - 1)) =
          ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (r + 1 + s) - 1) := by
        rw [← Finset.prod_range_reflect]
        apply Finset.prod_congr rfl
        intro s hs
        rw [Finset.mem_range] at hs
        congr 2
        omega
      have hB : (∏ i ∈ Finset.range (r + j), ((2 : ℚ) ^ (2 * (r + j) - j - i) - 1)) =
          ∏ s ∈ Finset.range (r + j), ((2 : ℚ) ^ (r + 1 + s) - 1) := by
        rw [← Finset.prod_range_reflect]
        apply Finset.prod_congr rfl
        intro s hs
        rw [Finset.mem_range] at hs
        congr 2
        omega
      have hP : (∏ i ∈ Finset.range (r + j), ((2 : ℚ) ^ (i + 1) - 1)) =
          (∏ i ∈ Finset.range r, ((2 : ℚ) ^ (i + 1) - 1)) * ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (r + 1 + s) - 1) := by
        rw [Finset.prod_range_add]
        congr 1
        apply Finset.prod_congr rfl
        intro s _
        congr 2
        omega
      have hLow : (∏ i ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ i)) =
          2 ^ (j * (j - 1) / 2) * ∏ s ∈ Finset.range j, ((2 : ℚ) ^ (s + 1) - 1) := by
        have h1 : ∀ i ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ i) = 2 ^ i * (2 ^ (j - i) - 1) := by
          intro i hi
          rw [Finset.mem_range] at hi
          rw [mul_sub, ← pow_add, Nat.add_sub_cancel' hi.le, mul_one]
        rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_pow_eq_pow_sum, Finset.sum_range_id]
        congr 1
        rw [← Finset.prod_range_reflect]
        apply Finset.prod_congr rfl
        intro s hs
        rw [Finset.mem_range] at hs
        congr 2
        omega
      have hHigh : ∀ (a c : ℕ), (∏ t ∈ Finset.range c, ((2 : ℚ) ^ j - 2 ^ (j + a + t))) =
          (-1) ^ c * 2 ^ (j * c) * ∏ t ∈ Finset.range c, ((2 : ℚ) ^ (a + t) - 1) := by
        intro a c
        have h1 : ∀ t ∈ Finset.range c, ((2 : ℚ) ^ j - 2 ^ (j + a + t)) = (-1) * 2 ^ j * (2 ^ (a + t) - 1) := by
          intro t _
          rw [add_assoc, pow_add]
          ring
        rw [Finset.prod_congr rfl h1, Finset.prod_mul_distrib, Finset.prod_mul_distrib, Finset.prod_const,
          Finset.prod_const, Finset.card_range, ← pow_mul]
      -- the excluded-index product splits at j
      have hErase : (∏ i ∈ (Finset.range (r + j + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i)) =
          (∏ i ∈ Finset.range j, ((2 : ℚ) ^ j - 2 ^ i)) * ∏ t ∈ Finset.range r, ((2 : ℚ) ^ j - 2 ^ (j + 1 + t)) := by
        have hset : (Finset.range (r + j + 1)).erase j = Finset.range j ∪ Finset.Ico (j + 1) (r + j + 1) := by
          ext i
          simp only [Finset.mem_erase, Finset.mem_range, Finset.mem_union, Finset.mem_Ico]
          omega
        have hdisj : Disjoint (Finset.range j) (Finset.Ico (j + 1) (r + j + 1)) := by
          rw [Finset.disjoint_left]
          intro i hi hi'
          simp only [Finset.mem_range, Finset.mem_Ico] at hi hi'
          omega
        rw [hset, Finset.prod_union hdisj, Finset.prod_Ico_eq_prod_range]
        congr 1
        have : r + j + 1 - (j + 1) = r := by omega
        rw [this]
      have hRHS : (∏ m ∈ Finset.Ico (r + j + 1) (2 * (r + j) + 1), ((2 : ℚ) ^ j - 2 ^ m)) =
          ∏ t ∈ Finset.range (r + j), ((2 : ℚ) ^ j - 2 ^ (j + (r + 1) + t)) := by
        rw [Finset.prod_Ico_eq_prod_range]
        have : 2 * (r + j) + 1 - (r + j + 1) = r + j := by omega
        rw [this]
        apply Finset.prod_congr rfl
        intro t _
        congr 2
        omega
      have hXne : (∏ s ∈ Finset.range j, ((2 : ℚ) ^ (r + 1 + s) - 1)) ≠ 0 := by
        rw [Finset.prod_ne_zero_iff]
        intro i _
        have : (1 : ℚ) < 2 ^ (r + 1 + i) := one_lt_pow₀ (by norm_num) (by omega)
        linarith
      have hH1 := hHigh 1 r
      have hH1' : (∏ t ∈ Finset.range r, ((2 : ℚ) ^ (1 + t) - 1)) = ∏ t ∈ Finset.range r, ((2 : ℚ) ^ (t + 1) - 1) := by
        apply Finset.prod_congr rfl
        intro t _
        rw [add_comm]
      have hH2 := hHigh (r + 1) (r + j)
      have hexp : (2 : ℚ) ^ (j * (j - 1) / 2) * 2 ^ (j * (j - 1) / 2) * 2 ^ j * 2 ^ (j * r) = 2 ^ (j * (r + j)) := by
        rw [← pow_add, ← pow_add, ← pow_add]
        congr 1
        have h2 : j * (j - 1) / 2 * 2 = j * (j - 1) := Nat.div_mul_cancel (Nat.even_mul_pred_self j).two_dvd
        rcases j with _ | i
        · simp
        · simp only [Nat.add_sub_cancel] at h2 ⊢
          nlinarith [h2]
      rw [Finset.prod_div_distrib, Finset.prod_div_distrib, hA, hB, hP, hErase, hLow, hH1, hH1', hRHS, hH2]
      rw [← hexp, pow_add]
      have h1 := hPne j
      have h2 := hPne r
      field_simp
    have odd_part : ∀ (n k : ℕ) (hk : k ≤ n) (c : ℕ → ℤ),
        ∃ z : ℤ, (z : ℚ) = (∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ m - 1)) *
          ∑ j ∈ Finset.range (k + 1), (c j : ℚ) / ((2 : ℚ) ^ (k - j) - 1) := by
      intro n k hk c
      -- every 2^m - 1 with 1 ≤ m ≤ n divides the product over the upper half (n/2, n]
      have key : ∀ m : ℕ, 1 ≤ m → m ≤ n →
          ((2 : ℤ) ^ m - 1) ∣ ∏ i ∈ Finset.Ioc (n / 2) n, ((2 : ℤ) ^ i - 1) := by
        intro m hm1 hmn
        have ht1 : 1 ≤ n / m := (Nat.one_le_div_iff (by omega)).2 hmn
        have hle : m * (n / m) ≤ n := Nat.mul_div_le n m
        have hlt : n < m * (n / m) + m := by
          have := Nat.lt_mul_div_succ n (show 0 < m by omega)
          rw [Nat.mul_succ] at this
          exact this
        have hmem : m * (n / m) ∈ Finset.Ioc (n / 2) n := by
          rw [Finset.mem_Ioc]
          constructor
          · have : m ≤ m * (n / m) := Nat.le_mul_of_pos_right m (by omega)
            omega
          · exact hle
        have h1 : ((2 : ℤ) ^ m - 1) ∣ (2 : ℤ) ^ (m * (n / m)) - 1 := by
          have := sub_dvd_pow_sub_pow ((2 : ℤ) ^ m) 1 (n / m)
          rwa [one_pow, ← pow_mul] at this
        exact h1.trans (Finset.dvd_prod_of_mem _ hmem)
      refine ⟨∑ j ∈ Finset.range (k + 1),
          c j * ((∏ i ∈ Finset.Ioc (n / 2) n, ((2 : ℤ) ^ i - 1)) / ((2 : ℤ) ^ (k - j) - 1)), ?_⟩
      rw [Int.cast_sum, Finset.mul_sum]
      apply Finset.sum_congr rfl
      intro j hj
      rw [Finset.mem_range] at hj
      by_cases h0 : k - j = 0
      · simp [h0]
      · obtain ⟨q, hq⟩ := key (k - j) (by omega) (by omega)
        have hne : ((2 : ℤ) ^ (k - j) - 1) ≠ 0 := by
          have : (2 : ℤ) ^ 1 ≤ 2 ^ (k - j) := pow_le_pow_right₀ (by norm_num) (by omega)
          linarith
        have hneq : ((2 : ℚ) ^ (k - j) - 1) ≠ 0 := by
          have : (2 : ℚ) ^ 1 ≤ 2 ^ (k - j) := pow_le_pow_right₀ (by norm_num) (by omega)
          linarith
        have hP : (∏ i ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ i - 1)) = ((2 : ℚ) ^ (k - j) - 1) * (q : ℚ) := by
          have := congrArg (fun z : ℤ => (z : ℚ)) hq
          push_cast at this
          exact this
        rw [hq, Int.mul_ediv_cancel_left _ hne, hP]
        push_cast
        field_simp
    have hres : ∀ j ≤ n, Qc n j * 2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
        ∏ m ∈ Finset.Ico (n + 1) (2 * n + 1), ((2 : ℚ) ^ j - 2 ^ m) := by
      intro j hj
      subst hQc
      exact residue n j hj
    have hform : ∀ j ≤ n, ∃ g : ℤ, Qc n j = (-1) ^ j * 2 ^ (j * (j - 1) / 2) * g := by
      intro j hj
      obtain ⟨z, hz⟩ := hQcint j hj
      refine ⟨(-1) ^ j * z, ?_⟩
      have h1 : ((-1 : ℚ) ^ j) ^ 2 = 1 := by
        rw [← pow_mul, mul_comm, pow_mul]
        simp
      push_cast
      linear_combination -hz - (z : ℚ) * 2 ^ (j * (j - 1) / 2) * h1
    obtain ⟨A, hA⟩ := two_adic_core (Qc n) n k hk hform hres
    -- the odd part: M_n clears the sum, since every Qc n j (j ≤ n) is an integer
    have hcint : ∀ j ≤ n, ∃ c : ℤ, Qc n j = c := by
      intro j hj
      obtain ⟨z, hz⟩ := hQcint j hj
      exact ⟨z * 2 ^ (j * (j - 1) / 2), by push_cast; rw [← hz]⟩
    choose! cf hcf using hcint
    obtain ⟨N, hN⟩ := odd_part n k hk cf
    have hsum : ∑ j ∈ Finset.range (k + 1), (cf j : ℚ) / ((2 : ℚ) ^ (k - j) - 1) =
        ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1) := by
      apply Finset.sum_congr rfl
      intro j hj
      rw [Finset.mem_range] at hj
      rw [hcf j (by omega)]
    rw [hsum] at hN
    have hMcast : ((∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1) : ℕ) : ℚ) = ∏ m ∈ Finset.Ioc (n / 2) n, ((2 : ℚ) ^ m - 1) := by
      push_cast [Nat.cast_prod]
      apply Finset.prod_congr rfl
      intro m _
      rw [Nat.cast_sub Nat.one_le_two_pow]
      push_cast
      ring
    set Bn : ℤ := ∏ s ∈ Finset.range (2 * n), ((2 : ℤ) ^ (s + 1) - 1) with hBn
    set Mz : ℤ := ((∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1) : ℕ) : ℤ) with hMz
    have hq : ((Bn * N : ℤ) : ℚ) = ((2 ^ (k * (k - 1) / 2) * (Mz * A) : ℤ) : ℚ) := by
      push_cast
      rw [hN, ← hMcast]
      have : ((Mz : ℤ) : ℚ) = ((∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1) : ℕ) : ℚ) := by
        rw [hMz]; push_cast; rfl
      rw [this]
      linear_combination ((∏ m ∈ Finset.Ioc (n / 2) n, (2 ^ m - 1) : ℕ) : ℚ) * hA
    have hzq : Bn * N = 2 ^ (k * (k - 1) / 2) * (Mz * A) := by exact_mod_cast hq
    have hcop : IsCoprime ((2 : ℤ) ^ (k * (k - 1) / 2)) Bn := (Int.isCoprime_two_left.2 (bn_odd n)).pow_left
    have hdvd : (2 : ℤ) ^ (k * (k - 1) / 2) ∣ N :=
      hcop.dvd_of_dvd_mul_left ⟨Mz * A, hzq⟩
    obtain ⟨z, hz⟩ := hdvd
    refine ⟨z, ?_⟩
    rw [hMcast, ← hN, hz]
    push_cast
    ring
  have hQcint : ∀ j ≤ n, ∃ z : ℤ, (z : ℚ) * (2 : ℚ) ^ (j * (j - 1) / 2) = Qc n j := by
    intro j _
    obtain ⟨z1, hz1⟩ := gauss n j
    obtain ⟨z2, hz2⟩ := gauss (2 * n - j) n
    refine ⟨(-1) ^ j * z1 * z2, ?_⟩
    subst hQc
    simp only []
    rw [← hz1, ← hz2]
    push_cast
    ring
  obtain ⟨z, hz⟩ := pint Qc hQc n hQcint k hk
  refine ⟨z, ?_⟩
  rw [hz]
  congr 1
  push_cast [Nat.cast_prod]
  apply Finset.prod_congr rfl
  intro m _
  rw [Nat.cast_sub Nat.one_le_two_pow]
  push_cast
  ring
