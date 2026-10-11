import Mathlib
import Nodes.«spec-ffd3137a».Context

/-- erdos-1050, hole `hpint` of the skeleton on erdos-1050--h1-v2--h3 (graph PR #253): a closed form
for the Padé numerator coefficient p_k = ∑_{j<k} Qc n j / (2^(k-j) - 1), k ≤ n (the j = k term is
0 in ℚ). It is the regular part at z = 2^k of the rational function ∑_j Qc n j / (z/2^j - 1), whose
product form is spec-f2b55478's, corrected for the terms j > k that p_k leaves out. Every term on the
right has 2-adic valuation at least k(k-1)/2, which is the 2-adic half of `hpint`. Checked exactly
(Python fractions) for 1 ≤ n ≤ 13 and every k ≤ n, and with 2 replaced by 3 and 5. -/
theorem erdos_1050_pade_numerator_closed_form : ∀ (Qc : ℕ → ℕ → ℚ),
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
  intro Qc hQc n k hk
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
  have hres : ∀ j ≤ n, Qc n j * 2 ^ j * ∏ i ∈ (Finset.range (n + 1)).erase j, ((2 : ℚ) ^ j - 2 ^ i) =
      ∏ m ∈ Finset.Ico (n + 1) (2 * n + 1), ((2 : ℚ) ^ j - 2 ^ m) := by
    intro j hj
    subst hQc
    exact residue n j hj
  have hstar := star n k hk (Qc n) hres
  have pos : ∀ t : ℕ, 1 ≤ t → (2 : ℚ) ^ t - 1 ≠ 0 := by
    intro t ht
    have : (1 : ℚ) < 2 ^ t := one_lt_pow₀ (by norm_num) (by omega)
    linarith
  -- 2^k/(2^k-2^m) = 1/(1-2^(m-k)) for k < m;  2^m/(2^m-2^i) = 2^(m-i)/(2^(m-i)-1) for i < m
  have qa : ∀ m : ℕ, k < m → (2 : ℚ) ^ k / (2 ^ k - 2 ^ m) = 1 / (1 - 2 ^ (m - k)) := by
    intro m hkm
    have hm : (2 : ℚ) ^ m = 2 ^ k * 2 ^ (m - k) := by rw [← pow_add, Nat.add_sub_cancel' hkm.le]
    have h1 : (1 : ℚ) - 2 ^ (m - k) ≠ 0 := by
      have := pos (m - k) (by omega)
      intro h; apply this; linarith
    have hk2 : (2 : ℚ) ^ k ≠ 0 := by positivity
    rw [hm, show (2 : ℚ) ^ k - 2 ^ k * 2 ^ (m - k) = 2 ^ k * (1 - 2 ^ (m - k)) by ring]
    field_simp
  have qb : ∀ i m : ℕ, i < m → (2 : ℚ) ^ m / (2 ^ m - 2 ^ i) = 2 ^ (m - i) / (2 ^ (m - i) - 1) := by
    intro i m him
    have hm : (2 : ℚ) ^ m = 2 ^ i * 2 ^ (m - i) := by rw [← pow_add, Nat.add_sub_cancel' him.le]
    have h1 := pos (m - i) (by omega)
    have hi : (2 : ℚ) ^ i ≠ 0 := by positivity
    rw [hm, show (2 : ℚ) ^ i * 2 ^ (m - i) - 2 ^ i = 2 ^ i * (2 ^ (m - i) - 1) by ring]
    field_simp
  have hsplit : (Finset.range (n + 1)).erase k = Finset.range k ∪ Finset.Ioc k n := by
    ext i
    simp only [Finset.mem_erase, Finset.mem_range, Finset.mem_union, Finset.mem_Ioc]
    omega
  have hdisj : Disjoint (Finset.range k) (Finset.Ioc k n) := by
    rw [Finset.disjoint_left]
    intro i hi hi'
    simp only [Finset.mem_range, Finset.mem_Ioc] at hi hi'
    omega
  rw [hsplit, Finset.sum_union hdisj, Finset.sum_union hdisj] at hstar
  -- the left side: p_k as a sum over j < k
  have hp : ∑ j ∈ Finset.range (k + 1), Qc n j / ((2 : ℚ) ^ (k - j) - 1) =
      ∑ j ∈ Finset.range k, Qc n j * 2 ^ j / ((2 : ℚ) ^ k - 2 ^ j) := by
    rw [Finset.sum_range_succ, Nat.sub_self, pow_zero, sub_self, div_zero, add_zero]
    apply Finset.sum_congr rfl
    intro j hj
    rw [Finset.mem_range] at hj
    have hkj : (2 : ℚ) ^ k = 2 ^ j * 2 ^ (k - j) := by rw [← pow_add, Nat.add_sub_cancel' hj.le]
    have h1 := pos (k - j) (by omega)
    have hj2 : (2 : ℚ) ^ j ≠ 0 := by positivity
    rw [hkj, show (2 : ℚ) ^ j * 2 ^ (k - j) - 2 ^ j = 2 ^ j * (2 ^ (k - j) - 1) by ring]
    field_simp
  -- the four sums in the closed form's indexing
  have s1 : ∑ m ∈ Finset.Ico (n + 1) (2 * n + 1), 1 / ((2 : ℚ) ^ k - 2 ^ m) * 2 ^ k =
      ∑ i ∈ Finset.range n, 1 / (1 - (2 : ℚ) ^ (n + 1 + i - k)) := by
    rw [Finset.sum_Ico_eq_sum_range, show 2 * n + 1 - (n + 1) = n by omega]
    apply Finset.sum_congr rfl
    intro i _
    rw [← qa (n + 1 + i) (by omega)]
    ring
  have s2 : ∑ i ∈ Finset.range k, 1 / ((2 : ℚ) ^ k - 2 ^ i) * 2 ^ k =
      ∑ b ∈ Finset.range k, (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := by
    rw [← Finset.sum_range_reflect]
    apply Finset.sum_congr rfl
    intro b hb
    rw [Finset.mem_range] at hb
    rw [show (1 : ℚ) / (2 ^ k - 2 ^ (k - 1 - b)) * 2 ^ k = 2 ^ k / (2 ^ k - 2 ^ (k - 1 - b)) by ring,
      qb (k - 1 - b) k (by omega), show k - (k - 1 - b) = b + 1 by omega]
  have s3 : ∑ i ∈ Finset.Ioc k n, 1 / ((2 : ℚ) ^ k - 2 ^ i) * 2 ^ k =
      ∑ b ∈ Finset.range (n - k), 1 / (1 - (2 : ℚ) ^ (b + 1)) := by
    rw [← Finset.Ico_add_one_add_one_eq_Ioc, Finset.sum_Ico_eq_sum_range, show n + 1 - (k + 1) = n - k by omega]
    apply Finset.sum_congr rfl
    intro b _
    rw [show (1 : ℚ) / (2 ^ k - 2 ^ (k + 1 + b)) * 2 ^ k = 2 ^ k / (2 ^ k - 2 ^ (k + 1 + b)) by ring,
      qa (k + 1 + b) (by omega), show k + 1 + b - k = b + 1 by omega]
  have s4 : ∑ j ∈ Finset.Ioc k n, Qc n j * 2 ^ j / ((2 : ℚ) ^ k - 2 ^ j) =
      -∑ b ∈ Finset.range (n - k), Qc n (k + b + 1) * (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := by
    rw [← Finset.Ico_add_one_add_one_eq_Ioc, Finset.sum_Ico_eq_sum_range, show n + 1 - (k + 1) = n - k by omega,
      ← Finset.sum_neg_distrib]
    apply Finset.sum_congr rfl
    intro b _
    have hq := qb k (k + 1 + b) (by omega)
    rw [show k + 1 + b - k = b + 1 by omega] at hq
    rw [show k + b + 1 = k + 1 + b by omega, mul_div_assoc, mul_div_assoc,
      show (2 : ℚ) ^ (k + 1 + b) / (2 ^ k - 2 ^ (k + 1 + b)) = -(2 ^ (k + 1 + b) / (2 ^ (k + 1 + b) - 2 ^ k)) by
        rw [← div_neg, neg_sub], hq]
    ring
  rw [hp]
  have f1 : (∑ m ∈ Finset.Ico (n + 1) (2 * n + 1), 1 / ((2 : ℚ) ^ k - 2 ^ m)) * 2 ^ k =
      ∑ i ∈ Finset.range n, 1 / (1 - (2 : ℚ) ^ (n + 1 + i - k)) := by rw [Finset.sum_mul]; exact s1
  have f2 : (∑ i ∈ Finset.range k, 1 / ((2 : ℚ) ^ k - 2 ^ i)) * 2 ^ k =
      ∑ b ∈ Finset.range k, (2 : ℚ) ^ (b + 1) / ((2 : ℚ) ^ (b + 1) - 1) := by rw [Finset.sum_mul]; exact s2
  have f3 : (∑ i ∈ Finset.Ioc k n, 1 / ((2 : ℚ) ^ k - 2 ^ i)) * 2 ^ k =
      ∑ b ∈ Finset.range (n - k), 1 / (1 - (2 : ℚ) ^ (b + 1)) := by rw [Finset.sum_mul]; exact s3
  linear_combination hstar - s4 + Qc n k * (f1 - f2 - f3)
