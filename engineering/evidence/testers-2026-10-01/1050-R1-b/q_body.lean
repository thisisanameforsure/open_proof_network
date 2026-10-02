  have hsumZ : ∀ (s : Finset ℕ) (g : ℕ → ℝ), (∀ i ∈ s, ∃ z : ℤ, (z : ℝ) = g i) → ∃ z : ℤ, (z : ℝ) = ∑ i ∈ s, g i := by
    intro s g
    induction s using Finset.induction_on with
    | empty => intro _; exact ⟨0, by simp⟩
    | insert a s ha ih =>
      intro h
      obtain ⟨za, hza⟩ := h a (Finset.mem_insert_self a s)
      obtain ⟨zs, hzs⟩ := ih (fun i hi => h i (Finset.mem_insert_of_mem hi))
      exact ⟨za + zs, by rw [Finset.sum_insert ha]; push_cast; rw [hza, hzs]⟩
  -- (L0) the Lagrange basis sums to 1: the degree-0 case
  have h0 : ∀ s : Finset ℕ, s.Nonempty → ∑ k ∈ s, (1 : ℝ) / ∏ l ∈ s.erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - (k : ℤ))) = 1 := by
    intro s hs
    have hv : Set.InjOn (fun k : ℕ => ((2 : ℝ) ^ k)⁻¹) (s : Set ℕ) := by
      intro a _ b _ hab
      exact pow_right_injective₀ (by norm_num : (0 : ℝ) < 2) (by norm_num) (inv_injective hab)
    have hsum := congrArg (Polynomial.eval (0 : ℝ)) (Lagrange.sum_basis hv hs)
    rw [Polynomial.eval_finset_sum, Polynomial.eval_one] at hsum
    refine Eq.trans (Finset.sum_congr rfl (fun k hk => ?_)) hsum
    unfold Lagrange.basis
    rw [Polynomial.eval_prod, one_div, ← Finset.prod_inv_distrib]
    refine Finset.prod_congr rfl (fun l hl => ?_)
    have ha : (2 : ℝ) ^ k ≠ 0 := by positivity
    have hb : (2 : ℝ) ^ l ≠ 0 := by positivity
    simp only [Lagrange.basisDivisor, Polynomial.eval_mul, Polynomial.eval_C, Polynomial.eval_sub, Polynomial.eval_X]
    rw [zpow_sub₀ two_ne_zero, zpow_natCast, zpow_natCast,
      show ((2 : ℝ) ^ k)⁻¹ - ((2 : ℝ) ^ l)⁻¹ = (1 - (2 : ℝ) ^ l / (2 : ℝ) ^ k) * (-((2 : ℝ) ^ l)⁻¹) by field_simp; ring,
      mul_inv, zero_sub, mul_assoc, inv_mul_cancel₀ (neg_ne_zero.mpr (inv_ne_zero hb)), mul_one]
  -- (L) complete homogeneous sums at the nodes 2^k are integers
  have hW : ∀ N : ℕ, ∀ (s : Finset ℕ) (e : ℕ), s.card + e = N → ∃ z : ℤ, (z : ℝ) = ∑ k ∈ s, ((2 : ℝ) ^ k) ^ e / ∏ l ∈ s.erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - (k : ℤ))) := by
    intro N
    induction N with
    | zero =>
      intro s e h
      have hs : s = ∅ := Finset.card_eq_zero.mp (by omega)
      subst hs
      exact ⟨0, by simp⟩
    | succ N ih =>
      intro s e h
      rcases s.eq_empty_or_nonempty with rfl | hs
      · exact ⟨0, by simp⟩
      rcases Nat.eq_zero_or_pos e with rfl | he
      · exact ⟨1, by rw [Int.cast_one]; exact (h0 s hs).symm.trans (Finset.sum_congr rfl (fun k _ => by rw [pow_zero]))⟩
      obtain ⟨e', rfl⟩ : ∃ e', e = e' + 1 := ⟨e - 1, by omega⟩
      obtain ⟨a, ha⟩ := hs
      obtain ⟨z1, hz1⟩ := ih (s.erase a) (e' + 1) (by rw [Finset.card_erase_of_mem ha]; have := Finset.card_pos.mpr ⟨a, ha⟩; omega)
      obtain ⟨z2, hz2⟩ := ih s e' (by omega)
      refine ⟨z1 + 2 ^ a * z2, ?_⟩
      push_cast
      rw [hz1, hz2, ← Finset.add_sum_erase s (fun k => ((2 : ℝ) ^ k) ^ e' / ∏ l ∈ s.erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - (k : ℤ)))) ha, ← Finset.add_sum_erase s (fun k => ((2 : ℝ) ^ k) ^ (e' + 1) / ∏ l ∈ s.erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - (k : ℤ)))) ha, mul_add, Finset.mul_sum]
      rw [add_left_comm, ← Finset.sum_add_distrib]
      congr 1
      · rw [pow_succ]; ring
      · refine Finset.sum_congr rfl (fun k hk => ?_)
        have hka : k ≠ a := Finset.ne_of_mem_erase hk
        have hks : k ∈ s := Finset.mem_of_mem_erase hk
        have hmem : a ∈ s.erase k := Finset.mem_erase.mpr ⟨Ne.symm hka, ha⟩
        have hsplit := Finset.mul_prod_erase (s.erase k) (fun l => (1 - (2 : ℝ) ^ ((l : ℤ) - (k : ℤ)))) hmem
        rw [Finset.erase_right_comm] at hsplit
        rw [← hsplit]
        have hρ : (1 - (2 : ℝ) ^ ((a : ℤ) - (k : ℤ))) ≠ 0 := by
          intro h1
          have h2 : (2 : ℝ) ^ ((a : ℤ) - (k : ℤ)) = 2 ^ (0 : ℤ) := by rw [zpow_zero]; linarith
          have h3 := zpow_right_injective₀ (by norm_num : (0 : ℝ) < 2) (by norm_num) h2
          omega
        have hq : (1 - (2 : ℝ) ^ ((a : ℤ) - (k : ℤ))) * (1 - (2 : ℝ) ^ ((a : ℤ) - (k : ℤ)))⁻¹ = 1 := mul_inv_cancel₀ hρ
        have hak : (2 : ℝ) ^ a = (2 : ℝ) ^ ((a : ℤ) - (k : ℤ)) * 2 ^ k := by
          rw [zpow_sub₀ two_ne_zero, zpow_natCast, zpow_natCast]
          field_simp
        simp only [div_eq_mul_inv, mul_inv]
        rw [pow_succ, hak]
        linear_combination (-((2 : ℝ) ^ k) ^ e' * 2 ^ k * (∏ l ∈ (s.erase a).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - (k : ℤ))))⁻¹) * hq
  -- geometric sums in 2^(-m)
  have hgeo : ∀ m : ℕ, 1 ≤ m → ∀ k : ℕ, ∑ i ∈ Finset.Icc 1 k, (((2 : ℝ) ^ i)⁻¹) ^ m = (1 - (((2 : ℝ) ^ k) ^ m)⁻¹) / ((2 : ℝ) ^ m - 1) := by
    intro m hm k
    have hB : (2 : ℝ) ^ m - 1 ≠ 0 := by
      have : (2 : ℝ) ≤ 2 ^ m := by
        calc (2 : ℝ) = 2 ^ 1 := (pow_one 2).symm
          _ ≤ 2 ^ m := pow_le_pow_right₀ (by norm_num) hm
      linarith
    induction k with
    | zero => simp
    | succ k ih =>
      rw [Finset.sum_Icc_succ_top (by omega), ih, inv_pow, pow_succ, mul_pow]
      have hX : ((2 : ℝ) ^ k) ^ m ≠ 0 := by positivity
      have hY : (2 : ℝ) ^ m ≠ 0 := by positivity
      generalize ((2 : ℝ) ^ k) ^ m = X at hX ⊢
      generalize (2 : ℝ) ^ m = Y at hY hB ⊢
      field_simp
      ring
  have hdvd : ∀ n i : ℕ, 1 ≤ i → i ≤ n - 1 → ((2 : ℤ) ^ i - 1) ∣ ∏ k ∈ Finset.Icc ((n + 1) / 2) n, ((1 : ℤ) - 2 ^ k) := by
    intro n i hi1 hi2
    obtain ⟨k0, hk0⟩ : ∃ k0, k0 = i * (n / i) := ⟨_, rfl⟩
    have hle : k0 ≤ n := by rw [hk0, mul_comm]; exact Nat.div_mul_le_self n i
    have hlt : n < k0 + i := by rw [hk0]; have := Nat.lt_mul_div_succ n (by omega : 0 < i); linarith
    have hge : i ≤ k0 := by rw [hk0]; exact Nat.le_mul_of_pos_right i (Nat.div_pos (by omega) (by omega))
    have hmem : k0 ∈ Finset.Icc ((n + 1) / 2) n := Finset.mem_Icc.mpr ⟨by omega, hle⟩
    have h1 : ((2 : ℤ) ^ i - 1) ∣ (2 : ℤ) ^ k0 - 1 := by
      have := sub_dvd_pow_sub_pow ((2 : ℤ) ^ i) 1 (n / i)
      rw [one_pow, ← pow_mul, ← hk0] at this
      exact this
    have h2 : ((2 : ℤ) ^ i - 1) ∣ (1 : ℤ) - 2 ^ k0 := by
      have : (1 : ℤ) - 2 ^ k0 = -((2 : ℤ) ^ k0 - 1) := by ring
      rw [this]; exact (dvd_neg).mpr h1
    exact h2.trans (Finset.dvd_prod_of_mem (fun k => (1 : ℤ) - 2 ^ k) hmem)
  intro n hn
  -- the numerator polynomial has integer coefficients
  obtain ⟨α, hα⟩ : ∃ α : ℕ → ℤ, ∀ y : ℝ, ∏ t ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ t * y) = ∑ j ∈ Finset.range n, (α j : ℝ) * y ^ j := by
    refine ⟨fun j => (∏ t ∈ Finset.Icc 1 (n - 1), (1 - Polynomial.C ((2 : ℤ) ^ t) * Polynomial.X)).coeff j, fun y => ?_⟩
    have hdeg : (Polynomial.map (Int.castRingHom ℝ) (∏ t ∈ Finset.Icc 1 (n - 1), (1 - Polynomial.C ((2 : ℤ) ^ t) * Polynomial.X))).natDegree < n := by
      refine lt_of_le_of_lt (Polynomial.natDegree_map_le) ?_
      refine lt_of_le_of_lt (Polynomial.natDegree_prod_le _ _) ?_
      refine lt_of_le_of_lt (Finset.sum_le_sum (g := fun _ => 1) (fun t _ => ?_)) ?_
      · compute_degree
      · simp only [Finset.sum_const, smul_eq_mul, mul_one, Nat.card_Icc]; omega
    have hev := Polynomial.eval_eq_sum_range' hdeg y
    have hev2 : ∏ t ∈ Finset.Icc 1 (n - 1), (1 - (2 : ℝ) ^ t * y) = Polynomial.eval y (Polynomial.map (Int.castRingHom ℝ) (∏ t ∈ Finset.Icc 1 (n - 1), (1 - Polynomial.C ((2 : ℤ) ^ t) * Polynomial.X))) := by
      rw [Polynomial.map_prod, Polynomial.eval_prod]
      refine Finset.prod_congr rfl (fun t _ => ?_)
      simp
    rw [hev2, hev]
    refine Finset.sum_congr rfl (fun j _ => ?_)
    rw [Polynomial.coeff_map]
    rfl
  obtain ⟨D, hD⟩ : ∃ D : ℕ → ℝ, ∀ k, D k = ∏ l ∈ (Finset.Icc 1 n).erase k, (1 - (2 : ℝ) ^ ((l : ℤ) - (k : ℤ))) := ⟨fun k => _, fun k => rfl⟩
  have hA : ∀ (x : ℝ) (k : ℕ), ∏ t ∈ Finset.Icc 1 (n - 1), (1 - x * (2 : ℝ) ^ (t + k)) = ∑ j ∈ Finset.range n, (α j : ℝ) * (x * 2 ^ k) ^ j := by
    intro x k
    rw [← hα]
    refine Finset.prod_congr rfl (fun t _ => ?_)
    rw [pow_add]; ring
  simp only [← hD, hA]
  -- (a) one double sum
  have hswap : ∑ i ∈ Finset.Icc 1 n, (∑ k ∈ Finset.Icc i n, -(∑ j ∈ Finset.range n, (α j : ℝ) * (((2 : ℝ) ^ i)⁻¹ * 2 ^ k) ^ j) / D k) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ i)⁻¹ = ∑ k ∈ Finset.Icc 1 n, ∑ i ∈ Finset.Icc 1 k, (-(∑ j ∈ Finset.range n, (α j : ℝ) * (((2 : ℝ) ^ i)⁻¹ * 2 ^ k) ^ j) / D k) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ i)⁻¹ := by
    simp only [Finset.sum_mul]
    refine Finset.sum_comm' (fun i k => ?_)
    simp only [Finset.mem_Icc]
    omega
  rw [hswap]
  simp only [Finset.mul_sum]
  rw [← Finset.sum_sub_distrib]
  simp only [← Finset.sum_sub_distrib, ← sub_mul]
  -- (b) per (k, i)
  have hb : ∀ (k i : ℕ), 1 ≤ i → (-(∑ j ∈ Finset.range n, (α j : ℝ) * ((8 / 3 : ℝ) * 2 ^ k) ^ j) / D k - -(∑ j ∈ Finset.range n, (α j : ℝ) * (((2 : ℝ) ^ i)⁻¹ * 2 ^ k) ^ j) / D k) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ i)⁻¹ = (∑ j ∈ Finset.range n, ∑ s ∈ Finset.range j, (α j : ℝ) * ((2 : ℝ) ^ k) ^ j * ((8 / 3 : ℝ) ^ s * (((2 : ℝ) ^ i)⁻¹) ^ (j - s))) / D k := by
    intro k i hi
    have h2i : (2 : ℝ) ^ i ≠ 0 := by positivity
    have hne : (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ i) ≠ 0 := by
      have : (2 : ℝ) ≤ 2 ^ i := by
        calc (2 : ℝ) = 2 ^ 1 := (pow_one 2).symm
          _ ≤ 2 ^ i := pow_le_pow_right₀ (by norm_num) hi
      intro h0
      linarith
    have hch : (((2 : ℝ) ^ i)⁻¹ - (8 / 3 : ℝ)) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ i)⁻¹ = ((2 : ℝ) ^ i)⁻¹ := by
      rw [show (((2 : ℝ) ^ i)⁻¹ - (8 / 3 : ℝ)) = ((2 : ℝ) ^ i)⁻¹ * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ i) by field_simp, mul_assoc, mul_inv_cancel₀ hne, mul_one]
    have hj : ∀ j : ℕ, ((((2 : ℝ) ^ i)⁻¹) ^ j - (8 / 3 : ℝ) ^ j) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ i)⁻¹ = ∑ s ∈ Finset.range j, (8 / 3 : ℝ) ^ s * (((2 : ℝ) ^ i)⁻¹) ^ (j - s) := by
      intro j
      have hg := geom_sum₂_mul (8 / 3 : ℝ) (((2 : ℝ) ^ i)⁻¹) j
      have hg' : (((2 : ℝ) ^ i)⁻¹) ^ j - (8 / 3 : ℝ) ^ j = (∑ s ∈ Finset.range j, (8 / 3 : ℝ) ^ s * (((2 : ℝ) ^ i)⁻¹) ^ (j - 1 - s)) * (((2 : ℝ) ^ i)⁻¹ - (8 / 3 : ℝ)) := by
        linear_combination hg
      rw [hg', mul_assoc, hch, Finset.sum_mul]
      refine Finset.sum_congr rfl (fun s hs => ?_)
      have hs' := Finset.mem_range.mp hs
      rw [mul_assoc, ← pow_succ, show j - 1 - s + 1 = j - s by omega]
    have e1 : (-(∑ j ∈ Finset.range n, (α j : ℝ) * ((8 / 3 : ℝ) * 2 ^ k) ^ j) / D k - -(∑ j ∈ Finset.range n, (α j : ℝ) * (((2 : ℝ) ^ i)⁻¹ * 2 ^ k) ^ j) / D k) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ i)⁻¹ = ((∑ j ∈ Finset.range n, (α j : ℝ) * (((2 : ℝ) ^ i)⁻¹ * 2 ^ k) ^ j - ∑ j ∈ Finset.range n, (α j : ℝ) * ((8 / 3 : ℝ) * 2 ^ k) ^ j) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ i)⁻¹) / D k := by
      ring
    rw [e1, ← Finset.sum_sub_distrib, Finset.sum_mul]
    congr 1
    refine Finset.sum_congr rfl (fun j _ => ?_)
    rw [← Finset.mul_sum, ← hj j, mul_pow, mul_pow]
    ring
  -- (c) sum over i
  have hc : ∀ k : ℕ, ∑ i ∈ Finset.Icc 1 k, (-(∑ j ∈ Finset.range n, (α j : ℝ) * ((8 / 3 : ℝ) * 2 ^ k) ^ j) / D k - -(∑ j ∈ Finset.range n, (α j : ℝ) * (((2 : ℝ) ^ i)⁻¹ * 2 ^ k) ^ j) / D k) * (1 - (8 / 3 : ℝ) * (2 : ℝ) ^ i)⁻¹ = ∑ j ∈ Finset.range n, ∑ s ∈ Finset.range j, (α j : ℝ) * (8 / 3 : ℝ) ^ s * ((((2 : ℝ) ^ k) ^ j - ((2 : ℝ) ^ k) ^ s) / D k) / ((2 : ℝ) ^ (j - s) - 1) := by
    intro k
    rw [Finset.sum_congr rfl (fun i hi => hb k i (Finset.mem_Icc.mp hi).1), ← Finset.sum_div, Finset.sum_comm, Finset.sum_div]
    refine Finset.sum_congr rfl (fun j _ => ?_)
    rw [Finset.sum_comm, Finset.sum_div]
    refine Finset.sum_congr rfl (fun s hs => ?_)
    have hs' := Finset.mem_range.mp hs
    rw [Finset.sum_congr rfl (fun i _ => (mul_assoc _ _ _).symm), ← Finset.mul_sum, hgeo (j - s) (by omega) k]
    have hjs : ((2 : ℝ) ^ k) ^ j = ((2 : ℝ) ^ k) ^ s * ((2 : ℝ) ^ k) ^ (j - s) := by
      rw [← pow_add]; congr 1; omega
    have hZ : ((2 : ℝ) ^ k) ^ (j - s) * (((2 : ℝ) ^ k) ^ (j - s))⁻¹ = 1 := mul_inv_cancel₀ (by positivity)
    rw [hjs]
    linear_combination (-((α j : ℝ) * ((2 : ℝ) ^ k) ^ s * (8 / 3 : ℝ) ^ s / ((2 : ℝ) ^ (j - s) - 1) / D k)) * hZ
  rw [Finset.sum_congr rfl (fun k _ => hc k), Finset.sum_comm, Finset.mul_sum]
  refine hsumZ _ _ (fun j hj => ?_)
  rw [Finset.sum_comm, Finset.mul_sum]
  refine hsumZ _ _ (fun s hs => ?_)
  have hj' := Finset.mem_range.mp hj
  have hs' := Finset.mem_range.mp hs
  obtain ⟨wj, hwj⟩ := hW _ (Finset.Icc 1 n) j rfl
  obtain ⟨ws, hws⟩ := hW _ (Finset.Icc 1 n) s rfl
  obtain ⟨q, hq⟩ := hdvd n (j - s) (by omega) (by omega)
  have hqR : ∏ k ∈ Finset.Icc ((n + 1) / 2) n, ((1 : ℝ) - 2 ^ k) = ((2 : ℝ) ^ (j - s) - 1) * q := by exact_mod_cast hq
  have hB : (2 : ℝ) ^ (j - s) - 1 ≠ 0 := by
    have : (2 : ℝ) ≤ 2 ^ (j - s) := by
      calc (2 : ℝ) = 2 ^ 1 := (pow_one 2).symm
        _ ≤ 2 ^ (j - s) := pow_le_pow_right₀ (by norm_num) (by omega)
    linarith
  have h3 : (3 : ℝ) ^ n = 3 ^ (n - s) * 3 ^ s := by rw [← pow_add]; congr 1; omega
  have h83 : (8 / 3 : ℝ) ^ s * 3 ^ s = 8 ^ s := by rw [← mul_pow]; norm_num
  refine ⟨3 ^ (n - s) * 8 ^ s * q * α j * (wj - ws), ?_⟩
  simp only [← hD] at hwj hws
  push_cast
  rw [hwj, hws, hqR, h3, ← h83, ← Finset.sum_sub_distrib]
  rw [Finset.mul_sum, Finset.mul_sum]
  refine Finset.sum_congr rfl (fun k _ => ?_)
  field_simp
