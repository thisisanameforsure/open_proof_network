import Mathlib
open Polynomial

-- Bn = ∏_{t < 2n} (2^(t+1) - 1): odd, and divisible by every 2^t - 1 with 1 ≤ t ≤ 2n
theorem bn_odd (n : ℕ) : Odd (∏ t ∈ Finset.range (2 * n), ((2 : ℤ) ^ (t + 1) - 1)) := by
  apply Finset.prod_induction _ Odd (fun a b ha hb => ha.mul hb) odd_one
  intro t _
  exact ⟨2 ^ t - 1, by ring⟩

theorem bn_dvd (n t : ℕ) (h1 : 1 ≤ t) (h2 : t ≤ 2 * n) :
    ((2 : ℤ) ^ t - 1) ∣ ∏ s ∈ Finset.range (2 * n), ((2 : ℤ) ^ (s + 1) - 1) := by
  have hm : t - 1 ∈ Finset.range (2 * n) := Finset.mem_range.2 (by omega)
  have := Finset.dvd_prod_of_mem (fun s => ((2 : ℤ) ^ (s + 1) - 1)) hm
  simpa [Nat.sub_add_cancel h1] using this

theorem good_basic (n c e t : ℕ) (g : ℤ) (he : c ≤ e) (h1 : 1 ≤ t) (h2 : t ≤ 2 * n) :
    ∃ A : ℤ, ((∏ s ∈ Finset.range (2 * n), ((2 : ℤ) ^ (s + 1) - 1) : ℤ) : ℚ) * ((2 : ℚ) ^ e * g / ((2 : ℚ) ^ t - 1)) =
      (2 : ℚ) ^ c * A := by
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


theorem lagrange_fp (s : Finset ℕ) (x : ℕ → ℚ) (hx : Set.InjOn x s) (r : ℕ → ℚ) (N : ℚ[X])
    (hN : N.natDegree < s.card)
    (hr : ∀ j ∈ s, r j * ∏ i ∈ s.erase j, (x j - x i) = N.eval (x j)) :
    N = ∑ j ∈ s, C (r j) * ∏ i ∈ s.erase j, (X - C (x i)) := by
  have hdeg : (∑ j ∈ s, C (r j) * ∏ i ∈ s.erase j, (X - C (x i)) - N).natDegree < s.card := by
    have hs : 0 < s.card := by
      rcases Nat.eq_zero_or_pos s.card with h | h
      · omega
      · exact h
    refine lt_of_le_of_lt (natDegree_sub_le _ _) (max_lt ?_ hN)
    refine lt_of_le_of_lt (natDegree_sum_le_of_forall_le s _ (n := s.card - 1) ?_) (by omega)
    intro j hj
    refine (natDegree_C_mul_le _ _).trans ?_
    rw [natDegree_finsetProd_X_sub_C_eq_card, Finset.card_erase_of_mem hj]
  have hzero : ∑ j ∈ s, C (r j) * ∏ i ∈ s.erase j, (X - C (x i)) - N = 0 := by
    apply eq_zero_of_natDegree_lt_card_of_eval_eq_zero' _ (s.image x)
    · intro y hy
      obtain ⟨i, hi, rfl⟩ := Finset.mem_image.1 hy
      rw [eval_sub, eval_finsetSum, Finset.sum_eq_single i]
      · rw [eval_mul, eval_C, eval_prod]
        simp only [eval_sub, eval_X, eval_C]
        rw [hr i hi, sub_self]
      · intro j hj hji
        rw [eval_mul, eval_prod]
        apply mul_eq_zero_of_right
        apply Finset.prod_eq_zero (i := i)
        · exact Finset.mem_erase.2 ⟨Ne.symm hji, hi⟩
        · simp
      · intro h; exact absurd hi h
    · rw [Finset.card_image_of_injOn hx]; exact hdeg
  exact (sub_eq_zero.1 hzero).symm

theorem deriv_eval (s : Finset ℕ) (x : ℕ → ℚ) (hx : Set.InjOn x s) (r : ℕ → ℚ) (k : ℕ) (hk : k ∈ s) :
    (derivative (∑ j ∈ s, C (r j) * ∏ i ∈ s.erase j, (X - C (x i)))).eval (x k) =
      (∏ i ∈ s.erase k, (x k - x i)) *
        (∑ j ∈ s.erase k, r j / (x k - x j) + r k * ∑ i ∈ s.erase k, 1 / (x k - x i)) := by
  have hne : ∀ i ∈ s.erase k, x k - x i ≠ 0 := by
    intro i hi h
    have hik := (Finset.mem_erase.1 hi)
    exact hik.1 (hx hik.2 hk (sub_eq_zero.1 h).symm)
  have hD : ∀ a ∈ s.erase k, ∏ b ∈ (s.erase k).erase a, (x k - x b) = (∏ i ∈ s.erase k, (x k - x i)) / (x k - x a) := by
    intro a ha
    rw [eq_div_iff (hne a ha), mul_comm]
    exact Finset.mul_prod_erase (s.erase k) (fun b => x k - x b) ha
  rw [derivative_sum, eval_finsetSum, ← Finset.add_sum_erase _ _ hk]
  have hterm : ∀ j ∈ s.erase k, (derivative (C (r j) * ∏ i ∈ s.erase j, (X - C (x i)))).eval (x k) =
      r j * ((∏ i ∈ s.erase k, (x k - x i)) / (x k - x j)) := by
    intro j hj
    rw [derivative_C_mul, eval_mul, eval_C, derivative_prod_finset, eval_finsetSum]
    congr 1
    have hkj : k ∈ s.erase j := Finset.mem_erase.2 ⟨fun h => (Finset.mem_erase.1 hj).1 h.symm, hk⟩
    rw [Finset.sum_eq_single k]
    · rw [derivative_X_sub_C, mul_one, eval_prod]
      simp only [eval_sub, eval_X, eval_C]
      rw [Finset.erase_right_comm]
      exact hD j hj
    · intro a ha hak
      rw [eval_mul, eval_prod]
      apply mul_eq_zero_of_left
      apply Finset.prod_eq_zero (i := k)
      · exact Finset.mem_erase.2 ⟨fun h => hak h.symm, hkj⟩
      · simp
    · intro h; exact absurd hkj h
  rw [Finset.sum_congr rfl hterm]
  rw [derivative_C_mul, eval_mul, eval_C, derivative_prod_finset, eval_finsetSum]
  have hself : ∀ a ∈ s.erase k, ((∏ b ∈ (s.erase k).erase a, (X - C (x b))) * derivative (X - C (x a))).eval (x k) =
      (∏ i ∈ s.erase k, (x k - x i)) / (x k - x a) := by
    intro a ha
    rw [derivative_X_sub_C, mul_one, eval_prod]
    simp only [eval_sub, eval_X, eval_C]
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


theorem nprod_deriv (T : Finset ℕ) (y : ℕ → ℚ) (z : ℚ) (hz : ∀ m ∈ T, z - y m ≠ 0) :
    (derivative (∏ m ∈ T, (X - C (y m)))).eval z = (∏ m ∈ T, (z - y m)) * ∑ m ∈ T, 1 / (z - y m) := by
  rw [derivative_prod_finset, eval_finsetSum, Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro m hm
  rw [derivative_X_sub_C, mul_one, eval_prod]
  simp only [eval_sub, eval_X, eval_C]
  rw [← Finset.mul_prod_erase T (fun b => z - y b) hm]
  field_simp [hz m hm]

theorem star (n k : ℕ) (hk : k ≤ n) (a : ℕ → ℚ)
    (ha : ∀ j ≤ n, a j * 2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
      ∏ m ∈ Finset.Ico (n + 1) (2 * n + 1), ((2 : ℚ) ^ j - 2 ^ m)) :
    ∑ j ∈ (Finset.range (n + 1)).erase k, a j * 2 ^ j / ((2 : ℚ) ^ k - 2 ^ j) =
      a k * 2 ^ k * (∑ m ∈ Finset.Ico (n + 1) (2 * n + 1), 1 / ((2 : ℚ) ^ k - 2 ^ m) -
        ∑ i ∈ (Finset.range (n + 1)).erase k, 1 / ((2 : ℚ) ^ k - 2 ^ i)) := by
  have hinj : ∀ a b : ℕ, (2 : ℚ) ^ a = 2 ^ b → a = b := by
    intro a b h
    have h' : (2 : ℕ) ^ a = 2 ^ b := by exact_mod_cast h
    exact Nat.pow_right_injective (le_refl 2) h'
  have hx : Set.InjOn (fun i : ℕ => (2 : ℚ) ^ i) (Finset.range (n + 1) : Set ℕ) :=
    fun a _ b _ h => hinj a b h
  have hkmem : k ∈ Finset.range (n + 1) := Finset.mem_range.2 (by omega)
  have hN : (∏ m ∈ Finset.Ico (n + 1) (2 * n + 1), (X - C ((2 : ℚ) ^ m))).natDegree < (Finset.range (n + 1)).card := by
    rw [natDegree_finsetProd_X_sub_C_eq_card, Nat.card_Ico, Finset.card_range]
    omega
  have hr : ∀ j ∈ Finset.range (n + 1), a j * 2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
      (∏ m ∈ Finset.Ico (n + 1) (2 * n + 1), (X - C ((2 : ℚ) ^ m))).eval ((2 : ℚ) ^ j) := by
    intro j hj
    rw [ha j (by simp at hj; omega), eval_prod]
    simp only [eval_sub, eval_X, eval_C]
  have hL := lagrange_fp (Finset.range (n + 1)) (fun i => (2 : ℚ) ^ i) hx (fun j => a j * 2 ^ j) _ hN hr
  have hdiff := congrArg (fun p => (derivative p).eval ((2 : ℚ) ^ k)) hL
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

theorem two_adic_core (a : ℕ → ℚ) (n k : ℕ) (hk : k ≤ n)
    (hform : ∀ j ≤ n, ∃ g : ℤ, a j = (-1) ^ j * 2 ^ (j * (j - 1) / 2) * g)
    (ha : ∀ j ≤ n, a j * 2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
      ∏ m ∈ Finset.Ico (n + 1) (2 * n + 1), ((2 : ℚ) ^ j - 2 ^ m)) :
    ∃ A : ℤ, ((∏ s ∈ Finset.range (2 * n), ((2 : ℤ) ^ (s + 1) - 1) : ℤ) : ℚ) *
      (∑ j ∈ Finset.range (k + 1), a j / ((2 : ℚ) ^ (k - j) - 1)) = (2 : ℚ) ^ (k * (k - 1) / 2) * A := by
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
