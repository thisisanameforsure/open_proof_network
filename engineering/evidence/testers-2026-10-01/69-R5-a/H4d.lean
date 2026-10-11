import Mathlib
import Defs.Construction

/-- h4d, lemma 1 (pure Mathlib + the Mertens node as a hypothesis; no definitions).
Along a progression `c + W t`, `t < z^A`, with `W ≤ z`, the number of prime factors in
`(z, z^A]` is on average at most `log A + C₁`. -/
theorem erdos_69__h4d__l1
    (hMert : ∃ C : ℝ, 0 ≤ C ∧ ∀ x : ℕ, 2 ≤ x →
      |∑ p ∈ Nat.primesLE x, (1 : ℝ) / p - Real.log (Real.log (x : ℝ))| ≤ C) :
    ∃ C₁ : ℝ, 0 ≤ C₁ ∧ ∀ (W z A c : ℕ), 1 ≤ W → W ≤ z → 2 ≤ z → 1 ≤ A →
      ∑ t ∈ Finset.range (z ^ A),
        ((((c + W * t).primeFactors.filter (fun p => z < p ∧ p ≤ z ^ A)).card : ℕ) : ℝ)
        ≤ ((z ^ A : ℕ) : ℝ) * (Real.log A + C₁) := by
  obtain ⟨C, hC0, hC⟩ := hMert
  refine ⟨2 * C + 1, by linarith, ?_⟩
  intro W z A c hW hWz hz hA
  obtain ⟨T, hT⟩ : ∃ T : ℕ, T = z ^ A := ⟨_, rfl⟩
  rw [← hT]
  have hzT : z ≤ T := by rw [hT]; exact Nat.le_self_pow (by omega) z
  have hT2 : 2 ≤ T := le_trans hz hzT
  have hTR : (0 : ℝ) < (T : ℝ) := by exact_mod_cast (by omega : 0 < T)
  obtain ⟨S, hS⟩ : ∃ S : Finset ℕ, S = (Nat.primesLE T).filter (fun p => z < p) := ⟨_, rfl⟩
  have hSmem : ∀ p, p ∈ S ↔ (p ≤ T ∧ p.Prime) ∧ z < p := by
    intro p; rw [hS, Finset.mem_filter, Nat.mem_primesLE]
  -- counting solutions of p ∣ c + W t
  have hcount : ∀ p ∈ S, ((Finset.range T).filter (fun t => p ∣ c + W * t)).card ≤ T / p + 1 := by
    intro p hp
    obtain ⟨⟨_, hpp⟩, hzp⟩ := (hSmem p).1 hp
    have hcop : Nat.Coprime p W :=
      (Nat.Prime.coprime_iff_not_dvd hpp).2 (Nat.not_dvd_of_pos_of_lt (by omega) (by omega))
    have hmaps : ∀ t ∈ (Finset.range T).filter (fun t => p ∣ c + W * t),
        t / p ∈ Finset.range (T / p + 1) := by
      intro t ht
      rw [Finset.mem_filter, Finset.mem_range] at ht
      rw [Finset.mem_range]
      exact Nat.lt_succ_of_le (Nat.div_le_div_right ht.1.le)
    have hinj : Set.InjOn (fun t => t / p)
        ((Finset.range T).filter (fun t => p ∣ c + W * t) : Finset ℕ) := by
      intro t1 h1 t2 h2 he
      rw [Finset.mem_coe, Finset.mem_filter] at h1 h2
      have hmod : c + W * t1 ≡ c + W * t2 [MOD p] := by
        have e1 : (c + W * t1) % p = 0 := Nat.mod_eq_zero_of_dvd h1.2
        have e2 : (c + W * t2) % p = 0 := Nat.mod_eq_zero_of_dvd h2.2
        unfold Nat.ModEq; rw [e1, e2]
      have hmod2 : W * t1 ≡ W * t2 [MOD p] := Nat.ModEq.add_left_cancel' c hmod
      have hmod3 : t1 ≡ t2 [MOD p] := Nat.ModEq.cancel_left_of_coprime (by rwa [Nat.Coprime] at hcop) hmod2
      have hd : t1 / p = t2 / p := he
      have e1 := Nat.div_add_mod t1 p
      have e2 := Nat.div_add_mod t2 p
      unfold Nat.ModEq at hmod3
      rw [hd, hmod3] at e1
      omega
    have := Finset.card_le_card_of_injOn _ hmaps hinj
    rwa [Finset.card_range] at this
  -- pointwise: the count is at most the number of p ∈ S dividing
  have hpt : ∀ t : ℕ, ((c + W * t).primeFactors.filter (fun p => z < p ∧ p ≤ T)).card
      ≤ ∑ p ∈ S, if p ∣ c + W * t then 1 else 0 := by
    intro t
    rw [← Finset.card_filter]
    refine Finset.card_le_card fun p hp => ?_
    rw [Finset.mem_filter] at hp
    rw [Finset.mem_filter, hSmem]
    exact ⟨⟨⟨hp.2.2, Nat.prime_of_mem_primeFactors hp.1⟩, hp.2.1⟩, Nat.dvd_of_mem_primeFactors hp.1⟩
  have hnat : ∑ t ∈ Finset.range T, ((c + W * t).primeFactors.filter (fun p => z < p ∧ p ≤ T)).card
      ≤ ∑ p ∈ S, (T / p + 1) := by
    calc _ ≤ ∑ t ∈ Finset.range T, ∑ p ∈ S, (if p ∣ c + W * t then 1 else 0) :=
          Finset.sum_le_sum fun t _ => hpt t
      _ = ∑ p ∈ S, ∑ t ∈ Finset.range T, (if p ∣ c + W * t then 1 else 0) := Finset.sum_comm
      _ ≤ ∑ p ∈ S, (T / p + 1) := by
          refine Finset.sum_le_sum fun p hp => ?_
          rw [← Finset.card_filter]
          exact hcount p hp
  -- reals
  have hSpos : ∀ p ∈ S, (0 : ℝ) < (p : ℝ) := fun p hp => by
    have := ((hSmem p).1 hp).1.2.pos
    exact_mod_cast this
  have hreal : ((∑ p ∈ S, (T / p + 1) : ℕ) : ℝ) ≤ (T : ℝ) * ∑ p ∈ S, (1 : ℝ) / p + S.card := by
    push_cast
    rw [Finset.sum_add_distrib, Finset.mul_sum]
    have : ∑ p ∈ S, (1 : ℝ) = S.card := by simp
    rw [this]
    have : ∑ p ∈ S, (((T / p : ℕ)) : ℝ) ≤ ∑ p ∈ S, (T : ℝ) * (1 / p) := by
      refine Finset.sum_le_sum fun p hp => ?_
      rw [mul_one_div]
      exact Nat.cast_div_le
    linarith
  have hScard : (S.card : ℝ) ≤ T := by
    have hsub : S ⊆ Finset.Icc 1 T := by
      intro p hp
      rw [Finset.mem_Icc]
      exact ⟨((hSmem p).1 hp).1.2.pos, ((hSmem p).1 hp).1.1⟩
    have := Finset.card_le_card hsub
    rw [Nat.card_Icc] at this
    exact_mod_cast (by omega : S.card ≤ T)
  have hsplit : ∑ p ∈ S, (1 : ℝ) / p
      = ∑ p ∈ Nat.primesLE T, (1 : ℝ) / p - ∑ p ∈ Nat.primesLE z, (1 : ℝ) / p := by
    have h := Finset.sum_filter_add_sum_filter_not (Nat.primesLE T) (fun p => z < p)
      (fun p => (1 : ℝ) / p)
    have he : (Nat.primesLE T).filter (fun p => ¬ z < p) = Nat.primesLE z := by
      ext p
      rw [Finset.mem_filter, Nat.mem_primesLE, Nat.mem_primesLE]
      constructor
      · rintro ⟨⟨_, hp⟩, h2⟩; exact ⟨by omega, hp⟩
      · rintro ⟨h1, hp⟩; exact ⟨⟨by omega, hp⟩, by omega⟩
    rw [he, ← hS] at h
    linarith
  have hlogz : (0 : ℝ) < Real.log z := Real.log_pos (by exact_mod_cast (by omega : 1 < z))
  have hloglog : Real.log (Real.log (T : ℝ)) = Real.log A + Real.log (Real.log z) := by
    rw [hT]; push_cast
    rw [Real.log_pow, Real.log_mul (by exact_mod_cast (by omega : A ≠ 0)) hlogz.ne']
  have h1 := abs_le.1 (hC T hT2)
  have h2 := abs_le.1 (hC z hz)
  have hsum : ∑ p ∈ S, (1 : ℝ) / p ≤ Real.log A + 2 * C := by
    rw [hsplit]; rw [hloglog] at h1; linarith
  have hfin : ((∑ t ∈ Finset.range T,
      ((c + W * t).primeFactors.filter (fun p => z < p ∧ p ≤ T)).card : ℕ) : ℝ)
      ≤ (T : ℝ) * (Real.log A + (2 * C + 1)) := by
    have h3 : ((∑ t ∈ Finset.range T,
      ((c + W * t).primeFactors.filter (fun p => z < p ∧ p ≤ T)).card : ℕ) : ℝ)
        ≤ ((∑ p ∈ S, (T / p + 1) : ℕ) : ℝ) := by exact_mod_cast hnat
    have h4 : (T : ℝ) * ∑ p ∈ S, (1 : ℝ) / p ≤ (T : ℝ) * (Real.log A + 2 * C) :=
      mul_le_mul_of_nonneg_left hsum hTR.le
    linarith
  push_cast at hfin ⊢
  exact hfin

/-- h4d, lemma 2 (pure Mathlib): a positive `n ≤ T^B` has at most `B` prime factors above `T`. -/
theorem erdos_69__h4d__l2 : ∀ T n B : ℕ, 2 ≤ T → 0 < n → n ≤ T ^ B →
    (n.primeFactors.filter (fun p => T < p)).card ≤ B := by
  intro T n B hT hn hnB
  have h1 : T ^ (n.primeFactors.filter (fun p => T < p)).card
      ≤ ∏ p ∈ n.primeFactors.filter (fun p => T < p), p :=
    Finset.pow_card_le_prod _ _ _ fun p hp => (Finset.mem_filter.1 hp).2.le
  have h2 : (∏ p ∈ n.primeFactors.filter (fun p => T < p), p) ∣ ∏ p ∈ n.primeFactors, p :=
    Finset.prod_dvd_prod_of_subset _ _ _ (Finset.filter_subset _ _)
  have h3 : (∏ p ∈ n.primeFactors, p) ∣ n := Nat.prod_primeFactors_dvd n
  have h4 : T ^ (n.primeFactors.filter (fun p => T < p)).card ≤ T ^ B :=
    le_trans h1 (le_trans (Nat.le_of_dvd hn (dvd_trans h2 h3)) hnB)
  exact (Nat.pow_le_pow_iff_right (by omega)).1 h4

/-- h4d, lemma 3 (over the definitions; elementary sizes): every integer the tails read at
times `t < T`, `T ≥ modulus`, at depth `3M + k + 1`, is positive and at most `T^(8+k)`. -/
theorem erdos_69__h4d__l3 : ∀ (M P n₀ T t k : ℕ) (d : Fin M → Fin 6),
    Opn.E69.modulus M P ≤ T → n₀ < Opn.E69.modulus M P → t < T →
    0 < Opn.E69.dil M P d *
        (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M + (k + 1)) ∧
    Opn.E69.dil M P d *
        (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M + (k + 1)) ≤ T ^ (8 + k) := by
  intro M P n₀ T t k d hWT hn₀ ht
  have arith : ∀ T W dl st sp t M k n0 sh : ℕ, 2 ≤ T → W ≤ T → dl ≤ W → sp ≤ W → M ≤ W →
      n0 < W → sh ≤ dl * (3 * M * W) → st ≤ n0 + sh → t < T →
      dl * (st + sp * t + 3 * M + (k + 1)) ≤ T ^ (8 + k) := by
    intro T W dl st sp t M k n0 sh hT hW hdl hsp hM hn0 hsh hst ht
    have hdlT : dl ≤ T := hdl.trans hW
    have hMT : M ≤ T := hM.trans hW
    have e0 : sh ≤ T * (3 * T * T) :=
      hsh.trans (Nat.mul_le_mul hdlT (Nat.mul_le_mul (Nat.mul_le_mul_left 3 hMT) hW))
    have e2 : sp * t ≤ T * T := Nat.mul_le_mul (hsp.trans hW) ht.le
    have hT1 : 1 ≤ T := by omega
    have hTT : T ≤ T * T := Nat.le_mul_of_pos_left T hT1
    have hTTT : T * T ≤ T * T * T := Nat.le_mul_of_pos_right _ hT1
    have e0' : T * (3 * T * T) = 3 * (T * T * T) := by ring
    have hX1 : 1 ≤ T * T * T := by nlinarith
    have hXj : T * T * T ≤ T * T * T * (k + 1) := Nat.le_mul_of_pos_right _ (by omega)
    have hjX : k + 1 ≤ T * T * T * (k + 1) := Nat.le_mul_of_pos_left _ hX1
    have key : st + sp * t + 3 * M + (k + 1) ≤ 16 * (T * T * T * (k + 1)) := by omega
    have h16 : 16 ≤ T ^ 4 := by
      calc 16 = 2 ^ 4 := by norm_num
        _ ≤ T ^ 4 := Nat.pow_le_pow_left hT 4
    have hk : k + 1 ≤ T ^ k :=
      (Nat.lt_two_pow_self (n := k)).trans_le (Nat.pow_le_pow_left hT k)
    calc dl * (st + sp * t + 3 * M + (k + 1)) ≤ T * (T ^ 4 * (T * T * T * T ^ k)) :=
          Nat.mul_le_mul hdlT (key.trans (Nat.mul_le_mul h16 (Nat.mul_le_mul_left _ hk)))
      _ = T ^ (8 + k) := by ring
  -- facts about the construction
  have hdil2 : ∀ d' : Fin M → Fin 6, 2 ≤ Opn.E69.dil M P d' := by
    intro d'
    have : 0 < primorial P := primorial_pos P
    have : 1 * 1 ≤ primorial P * (1 + Opn.E69.gIndex M d') := Nat.mul_le_mul (by omega) (by omega)
    unfold Opn.E69.dil; omega
  have hmodpos : 0 < Opn.E69.modulus M P := by
    unfold Opn.E69.modulus
    exact Finset.prod_pos fun d' _ => by have := hdil2 d'; omega
  have hdvd : Opn.E69.dil M P d ∣ Opn.E69.modulus M P :=
    Finset.dvd_prod_of_mem _ (Finset.mem_univ d)
  have hdilW : Opn.E69.dil M P d ≤ Opn.E69.modulus M P := Nat.le_of_dvd hmodpos hdvd
  have hstepW : Opn.E69.step M P d ≤ Opn.E69.modulus M P := Nat.div_le_self _ _
  have hcard : (Finset.univ : Finset (Fin M → Fin 6)).card = 6 ^ M := by simp
  have hW2 : 2 ^ (6 ^ M) ≤ Opn.E69.modulus M P := by
    have h := Finset.pow_card_le_prod (Finset.univ : Finset (Fin M → Fin 6))
      (fun d' => Opn.E69.dil M P d') 2 (fun d' _ => hdil2 d')
    rwa [hcard] at h
  have h3M : 3 * M ≤ 6 ^ M := by
    rcases Nat.eq_zero_or_pos M with h0 | hpos
    · subst h0; norm_num
    · have h2 : (3 : ℕ) ^ 1 ≤ 3 ^ M := Nat.pow_le_pow_right (by norm_num) hpos
      have h3 : (6 : ℕ) ^ M = 3 ^ M * 2 ^ M := by rw [← Nat.mul_pow]
      rw [h3]
      exact Nat.mul_le_mul (by simpa using h2) (Nat.lt_two_pow_self (n := M)).le
  have h7W : 7 ^ M ≤ Opn.E69.modulus M P := by
    calc 7 ^ M ≤ 8 ^ M := Nat.pow_le_pow_left (by norm_num) M
      _ = 2 ^ (3 * M) := by rw [pow_mul]; norm_num
      _ ≤ 2 ^ (6 ^ M) := Nat.pow_le_pow_right (by norm_num) h3M
      _ ≤ _ := hW2
  have hMW : M ≤ Opn.E69.modulus M P :=
    ((Nat.lt_pow_self (by norm_num : 1 < 7) (n := M)).le).trans h7W
  have hsdig : ∀ (r : ℕ) (j : Fin 6), Opn.E69.sDigit r j ≤ 18 * r + 18 := by
    intro r j
    unfold Opn.E69.sDigit
    split_ifs <;> fin_cases j <;> simp <;> omega
  have hsI : Opn.E69.sIndex M d ≤ 3 * M * 7 ^ M := by
    have h1 : Opn.E69.sIndex M d ≤ ∑ r : Fin M, 7 ^ (r : ℕ) * (18 * M) :=
      Finset.sum_le_sum fun r _ => Nat.mul_le_mul_left _
        ((hsdig r (d r)).trans (by have := r.2; omega))
    have h2 : ∑ r : Fin M, 7 ^ (r : ℕ) * (18 * M) = ∑ r ∈ Finset.range M, 7 ^ r * (18 * M) :=
      Fin.sum_univ_eq_sum_range (fun r => 7 ^ r * (18 * M)) M
    have h3 : ∀ n : ℕ, ∑ r ∈ Finset.range n, 7 ^ r * (18 * M) + 3 * M = 3 * M * 7 ^ n := by
      intro n
      induction n with
      | zero => simp
      | succ n ih => rw [Finset.sum_range_succ, pow_succ]; nlinarith
    have := h3 M
    omega
  have hshift : Opn.E69.shift M P d
      ≤ Opn.E69.dil M P d * (3 * M * Opn.E69.modulus M P) := by
    unfold Opn.E69.shift
    refine Nat.mul_le_mul ?_ (hsI.trans (Nat.mul_le_mul_left _ h7W))
    have : primorial P * 1 ≤ primorial P * (1 + Opn.E69.gIndex M d) :=
      Nat.mul_le_mul_left _ (by omega)
    unfold Opn.E69.dil; omega
  have hstart : Opn.E69.start M P n₀ d ≤ n₀ + Opn.E69.shift M P d := Nat.div_le_self _ _
  have hT2 : 2 ≤ T := by
    have := hdil2 d; omega
  refine ⟨Nat.mul_pos (by have := hdil2 d; omega) (by omega), ?_⟩
  exact arith T _ _ _ _ t M k n₀ _ hT2 hWT hdilW hstepW hMW hn₀ hshift hstart ht

/-- h4d, lemma 4: the number of prime factors above `z` of the integers one line reads at one
depth, summed over `t < z^A`. From lemmas 1, 2, 3. -/
theorem erdos_69__h4d__l4 (C₁ : ℝ)
    (hl1 : ∀ (W z A c : ℕ), 1 ≤ W → W ≤ z → 2 ≤ z → 1 ≤ A →
      ∑ t ∈ Finset.range (z ^ A),
        ((((c + W * t).primeFactors.filter (fun p => z < p ∧ p ≤ z ^ A)).card : ℕ) : ℝ)
        ≤ ((z ^ A : ℕ) : ℝ) * (Real.log A + C₁)) :
    ∀ (M P z A n₀ k : ℕ) (d : Fin M → Fin 6), Opn.E69.modulus M P ≤ z → 1 ≤ A →
      n₀ < Opn.E69.modulus M P → Opn.E69.Admissible M P n₀ →
      ∑ t ∈ Finset.range (z ^ A), ((((Opn.E69.dil M P d *
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M + (k + 1))).primeFactors.filter
            (fun p => z < p)).card : ℕ) : ℝ)
        ≤ ((z ^ A : ℕ) : ℝ) * (Real.log A + C₁) + ((z ^ A : ℕ) : ℝ) * (8 + (k : ℝ)) := by
  intro M P z A n₀ k d hWz hA hn₀ hadm
  have hdil2 : 2 ≤ Opn.E69.dil M P d := by
    have : 0 < primorial P := primorial_pos P
    have : 1 * 1 ≤ primorial P * (1 + Opn.E69.gIndex M d) := Nat.mul_le_mul (by omega) (by omega)
    unfold Opn.E69.dil; omega
  have hmodpos : 0 < Opn.E69.modulus M P := by
    unfold Opn.E69.modulus
    refine Finset.prod_pos fun d' _ => ?_
    unfold Opn.E69.dil; omega
  have hdvd : Opn.E69.dil M P d ∣ Opn.E69.modulus M P :=
    Finset.dvd_prod_of_mem _ (Finset.mem_univ d)
  have hW2 : 2 ≤ Opn.E69.modulus M P := hdil2.trans (Nat.le_of_dvd hmodpos hdvd)
  have hz2 : 2 ≤ z := hW2.trans hWz
  have hzT : z ≤ z ^ A := Nat.le_self_pow (by omega) z
  have hN : ∀ t : ℕ, Opn.E69.dil M P d *
      (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M + (k + 1))
      = (n₀ + Opn.E69.shift M P d + Opn.E69.dil M P d * (3 * M + (k + 1)))
        + Opn.E69.modulus M P * t := by
    intro t
    have e1 : Opn.E69.dil M P d * Opn.E69.start M P n₀ d = n₀ + Opn.E69.shift M P d :=
      Nat.mul_div_cancel' (hadm d)
    have e2 : Opn.E69.dil M P d * Opn.E69.step M P d = Opn.E69.modulus M P :=
      Nat.mul_div_cancel' hdvd
    rw [← e1, ← e2]; ring
  have hpt : ∀ t ∈ Finset.range (z ^ A), ((((Opn.E69.dil M P d *
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M + (k + 1))).primeFactors.filter
            (fun p => z < p)).card : ℕ) : ℝ)
      ≤ (((((n₀ + Opn.E69.shift M P d + Opn.E69.dil M P d * (3 * M + (k + 1)))
          + Opn.E69.modulus M P * t).primeFactors.filter (fun p => z < p ∧ p ≤ z ^ A)).card : ℕ) : ℝ)
        + (8 + (k : ℝ)) := by
    intro t ht
    obtain ⟨hpos, hle⟩ := erdos_69__h4d__l3 M P n₀ (z ^ A) t k d (hWz.trans hzT) hn₀
      (Finset.mem_range.1 ht)
    have h2 := erdos_69__h4d__l2 (z ^ A) _ (8 + k) (hz2.trans hzT) hpos hle
    rw [hN t] at h2 ⊢
    obtain ⟨n, hn⟩ : ∃ n : ℕ, n = (n₀ + Opn.E69.shift M P d
      + Opn.E69.dil M P d * (3 * M + (k + 1))) + Opn.E69.modulus M P * t := ⟨_, rfl⟩
    rw [← hn] at h2 ⊢
    have hsub : n.primeFactors.filter (fun p => z < p)
        ⊆ n.primeFactors.filter (fun p => z < p ∧ p ≤ z ^ A)
          ∪ n.primeFactors.filter (fun p => z ^ A < p) := by
      intro p hp
      rw [Finset.mem_filter] at hp
      rw [Finset.mem_union, Finset.mem_filter, Finset.mem_filter]
      by_cases h : p ≤ z ^ A
      · exact Or.inl ⟨hp.1, hp.2, h⟩
      · exact Or.inr ⟨hp.1, by omega⟩
    have h3 := (Finset.card_le_card hsub).trans (Finset.card_union_le _ _)
    have h4 : (n.primeFactors.filter (fun p => z < p)).card
        ≤ (n.primeFactors.filter (fun p => z < p ∧ p ≤ z ^ A)).card + (8 + k) := by omega
    exact_mod_cast h4
  refine (Finset.sum_le_sum hpt).trans ?_
  rw [Finset.sum_add_distrib, Finset.sum_const, Finset.card_range, nsmul_eq_mul]
  have := hl1 (Opn.E69.modulus M P) z A
    (n₀ + Opn.E69.shift M P d + Opn.E69.dil M P d * (3 * M + (k + 1))) (by omega) hWz hz2 hA
  linarith

open scoped ArithmeticFunction.omega

/-- h4d, lemma 5: pointwise, the cost of cutting `ω` at `z` is at most `2^(-3M)` times the
weighted count of prime factors above `z` along the `6^M` lines from depth `3M` on. From h4b. -/
theorem erdos_69__h4d__l5
    (h4b : ∀ (M P n₀ t : ℕ), Even M → Opn.E69.Admissible M P n₀ →
      (Opn.E69.signedTail M P n₀ t = (1 / 2 ^ (3 * M) : ℝ) *
        ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) * Opn.E69.tail (Opn.E69.dil M P d)
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M)) ∧
      ∀ z : ℕ, Opn.E69.signedTailBelow z M P n₀ t = (1 / 2 ^ (3 * M) : ℝ) *
        ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) * Opn.E69.tailBelow z (Opn.E69.dil M P d)
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M)) :
    ∀ (M P z n₀ t : ℕ), Even M → Opn.E69.Admissible M P n₀ →
      (∀ d : Fin M → Fin 6, Summable (fun k : ℕ => ((((Opn.E69.dil M P d *
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M + (k + 1))).primeFactors.filter
            (fun p => z < p)).card : ℕ) : ℝ) / 2 ^ (k + 1))) ∧
      |Opn.E69.signedTail M P n₀ t - Opn.E69.signedTailBelow z M P n₀ t|
        ≤ (1 / 2 ^ (3 * M) : ℝ) * ∑ d : Fin M → Fin 6, ∑' k : ℕ, ((((Opn.E69.dil M P d *
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M + (k + 1))).primeFactors.filter
            (fun p => z < p)).card : ℕ) : ℝ) / 2 ^ (k + 1) := by
  intro M P z n₀ t hM hadm
  have hr : ‖(1 / 2 : ℝ)‖ < 1 := by norm_num
  have hS : Summable (fun k : ℕ => ((k : ℝ) + 1) * (1 / 2 : ℝ) ^ (k + 1)) := by
    have h0 := (hasSum_coe_mul_geometric_of_norm_lt_one hr).summable
    have h1 := (summable_nat_add_iff 1).2 h0
    simpa [Nat.cast_add, Nat.cast_one] using h1
  have hsumm : ∀ F : ℕ → ℕ, (∀ y, F y ≤ y + 1) → ∀ a m : ℕ,
      Summable (fun k : ℕ => (F (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)) := by
    intro F hF a m
    refine Summable.of_nonneg_of_le (fun k => by positivity) (fun k => ?_)
      (hS.mul_left ((((a * (m + 1) : ℕ) : ℝ)) + 1))
    have h : m + (k + 1) ≤ (m + 1) * (k + 1) := by nlinarith
    have h1 : F (a * (m + (k + 1))) ≤ (a * (m + 1) + 1) * (k + 1) := by
      have e : (a * (m + 1) + 1) * (k + 1) = a * ((m + 1) * (k + 1)) + (k + 1) := by ring
      have h3 := hF (a * (m + (k + 1)))
      have h4 : a * (m + (k + 1)) ≤ a * ((m + 1) * (k + 1)) := Nat.mul_le_mul_left a h
      omega
    have h2 : (F (a * (m + (k + 1))) : ℝ) ≤ (((a * (m + 1) : ℕ) : ℝ) + 1) * ((k : ℝ) + 1) := by
      exact_mod_cast h1
    have hp : (0 : ℝ) < 2 ^ (k + 1) := by positivity
    rw [div_le_iff₀ hp, one_div_pow, mul_assoc, mul_assoc, one_div_mul_cancel hp.ne', mul_one]
    exact h2
  have hω : ∀ y : ℕ, ω y = y.primeFactors.card := fun y => by
    rw [ArithmeticFunction.cardDistinctFactors_apply, Nat.primeFactors, List.card_toFinset]
  have hcard : ∀ y : ℕ, y.primeFactors.card ≤ y + 1 := by
    intro y
    have hsub : y.primeFactors ⊆ Finset.range (y + 1) := by
      intro p hp
      have hp' := Nat.mem_primeFactors.1 hp
      exact Finset.mem_range.2 (Nat.lt_succ_of_le (Nat.le_of_dvd (Nat.pos_of_ne_zero hp'.2.2) hp'.2.1))
    have := Finset.card_le_card hsub
    rwa [Finset.card_range] at this
  have hFω : ∀ y, (fun y => ω y) y ≤ y + 1 := fun y => by
    show ω y ≤ y + 1
    rw [hω]; exact hcard y
  have hFb : ∀ y, Opn.E69.omegaBelow z y ≤ y + 1 := fun y => by
    unfold Opn.E69.omegaBelow
    exact le_trans (Finset.card_le_card (Finset.filter_subset _ _)) (hcard y)
  have hFa : ∀ y, (fun y : ℕ => (y.primeFactors.filter (fun p => z < p)).card) y ≤ y + 1 :=
    fun y => le_trans (Finset.card_le_card (Finset.filter_subset _ _)) (hcard y)
  have hsplit : ∀ y : ℕ, (ω y : ℝ) - (Opn.E69.omegaBelow z y : ℝ)
      = (((y.primeFactors.filter (fun p => z < p)).card : ℕ) : ℝ) := by
    intro y
    have h := Finset.sum_filter_add_sum_filter_not y.primeFactors (fun p => p ≤ z)
      (fun _ => (1 : ℕ))
    simp only [Finset.sum_const, smul_eq_mul, mul_one] at h
    have e : y.primeFactors.filter (fun p => ¬ p ≤ z) = y.primeFactors.filter (fun p => z < p) := by
      refine Finset.filter_congr fun p _ => ?_
      omega
    rw [e] at h
    have h' : (Opn.E69.omegaBelow z y : ℝ)
        + (((y.primeFactors.filter (fun p => z < p)).card : ℕ) : ℝ) = (ω y : ℝ) := by
      rw [hω]; unfold Opn.E69.omegaBelow; exact_mod_cast h
    linarith
  have hdiff : ∀ a m : ℕ, Opn.E69.tail a m - Opn.E69.tailBelow z a m
      = ∑' k : ℕ, ((((a * (m + (k + 1))).primeFactors.filter (fun p => z < p)).card : ℕ) : ℝ)
          / 2 ^ (k + 1) := by
    intro a m
    unfold Opn.E69.tail Opn.E69.tailBelow
    rw [← Summable.tsum_sub (hsumm (fun y => ω y) hFω a m) (hsumm _ hFb a m)]
    refine tsum_congr fun k => ?_
    rw [← sub_div, hsplit]
  have hsign : ∀ d : Fin M → Fin 6, |(Opn.E69.sign M d : ℝ)| = 1 := by
    intro d
    have h : Opn.E69.sign M d = 1 ∨ Opn.E69.sign M d = -1 := by
      unfold Opn.E69.sign
      refine Finset.prod_induction _ (fun x : ℤ => x = 1 ∨ x = -1) ?_ (Or.inl rfl)
        (fun r _ => neg_one_pow_eq_or ℤ _)
      rintro x y (rfl | rfl) (rfl | rfl) <;> simp
    rcases h with h | h <;> rw [h] <;> simp
  refine ⟨fun d => ?_, ?_⟩
  · have := hsumm _ hFa (Opn.E69.dil M P d)
      (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M)
    exact this
  · obtain ⟨e1, e2⟩ := h4b M P n₀ t hM hadm
    rw [e1, e2 z, ← mul_sub, ← Finset.sum_sub_distrib, abs_mul,
      abs_of_nonneg (by positivity : (0 : ℝ) ≤ 1 / 2 ^ (3 * M))]
    refine mul_le_mul_of_nonneg_left ?_ (by positivity)
    refine (Finset.abs_sum_le_sum_abs _ _).trans (Finset.sum_le_sum fun d _ => ?_)
    rw [← mul_sub, abs_mul, hsign, one_mul, hdiff, abs_of_nonneg (tsum_nonneg fun k => by positivity)]

/-- h4d (large primes), from the Mertens node (as a hypothesis, the way the node's Context
supplies it) and h4b (inherited). Cutting `ω` at `z ≥ modulus` costs, in mean over `t < z^A`,
at most `C (3/4)^M (1 + log A)`. -/
theorem erdos_69__h4__h4
    (hMert : ∃ C : ℝ, 0 ≤ C ∧ ∀ x : ℕ, 2 ≤ x →
      |∑ p ∈ Nat.primesLE x, (1 : ℝ) / p - Real.log (Real.log (x : ℝ))| ≤ C)
    (h4b : ∀ (M P n₀ t : ℕ), Even M → Opn.E69.Admissible M P n₀ →
      (Opn.E69.signedTail M P n₀ t = (1 / 2 ^ (3 * M) : ℝ) *
        ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) * Opn.E69.tail (Opn.E69.dil M P d)
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M)) ∧
      ∀ z : ℕ, Opn.E69.signedTailBelow z M P n₀ t = (1 / 2 ^ (3 * M) : ℝ) *
        ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) * Opn.E69.tailBelow z (Opn.E69.dil M P d)
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M)) :
    ∃ C : ℕ, ∀ (M P z A n₀ : ℕ), Even M → 2 ≤ P → 7 ^ M ≤ P →
      Opn.E69.modulus M P ≤ z → 1 ≤ A → n₀ < Opn.E69.modulus M P → Opn.E69.Admissible M P n₀ →
      (∑ t ∈ Finset.range (z ^ A),
          |Opn.E69.signedTail M P n₀ t - Opn.E69.signedTailBelow z M P n₀ t|) / ((z ^ A : ℕ) : ℝ)
        ≤ (C : ℝ) * (3 / 4 : ℝ) ^ M * (1 + Real.log A) := by
  obtain ⟨C₁, hC₁0, hl1⟩ := erdos_69__h4d__l1 hMert
  have hr : ‖(1 / 2 : ℝ)‖ < 1 := by norm_num
  have hS : Summable (fun k : ℕ => ((k : ℝ) + 1) * (1 / 2 : ℝ) ^ (k + 1)) := by
    have h0 := (hasSum_coe_mul_geometric_of_norm_lt_one hr).summable
    have h1 := (summable_nat_add_iff 1).2 h0
    simpa [Nat.cast_add, Nat.cast_one] using h1
  obtain ⟨S₀, hS₀⟩ : ∃ S₀ : ℝ, S₀ = ∑' k : ℕ, ((k : ℝ) + 1) * (1 / 2 : ℝ) ^ (k + 1) := ⟨_, rfl⟩
  have hS₀0 : 0 ≤ S₀ := by rw [hS₀]; exact tsum_nonneg fun k => by positivity
  refine ⟨⌈S₀ * (C₁ + 8)⌉₊ + ⌈S₀⌉₊, ?_⟩
  intro M P z A n₀ hM hP2 hP7 hWz hA hn₀ hadm
  obtain ⟨T, hT⟩ : ∃ T : ℕ, T = z ^ A := ⟨_, rfl⟩
  have hl4 := fun k d => erdos_69__h4d__l4 C₁ hl1 M P z A n₀ k d hWz hA hn₀ hadm
  have hl5 := fun t => erdos_69__h4d__l5 h4b M P z n₀ t hM hadm
  rw [← hT] at hl4 ⊢
  have hlogA : 0 ≤ Real.log A := Real.log_natCast_nonneg A
  obtain ⟨a, ha⟩ : ∃ a : ℝ, a = Real.log A + C₁ + 8 := ⟨_, rfl⟩
  have ha1 : 1 ≤ a := by rw [ha]; linarith
  have hTpos : 0 < T := by
    rw [hT]
    refine Nat.pos_of_ne_zero (pow_ne_zero _ ?_)
    intro h0
    have hmodpos : 0 < Opn.E69.modulus M P := by
      unfold Opn.E69.modulus
      refine Finset.prod_pos fun d' _ => ?_
      unfold Opn.E69.dil; omega
    omega
  have hTR : (0 : ℝ) < (T : ℝ) := by exact_mod_cast hTpos
  -- per line
  have hline : ∀ d : Fin M → Fin 6, ∑ t ∈ Finset.range T, ∑' k : ℕ, ((((Opn.E69.dil M P d *
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M + (k + 1))).primeFactors.filter
            (fun p => z < p)).card : ℕ) : ℝ) / 2 ^ (k + 1) ≤ (T : ℝ) * a * S₀ := by
    intro d
    rw [← Summable.tsum_finsetSum (fun t _ => (hl5 t).1 d)]
    have hsm : Summable (fun k : ℕ => (T : ℝ) * a * (((k : ℝ) + 1) * (1 / 2 : ℝ) ^ (k + 1))) :=
      hS.mul_left _
    rw [hS₀, ← tsum_mul_left]
    refine Summable.tsum_le_tsum (fun k => ?_) (summable_sum fun t _ => (hl5 t).1 d) hsm
    rw [← Finset.sum_div]
    have hp : (0 : ℝ) < 2 ^ (k + 1) := by positivity
    rw [div_le_iff₀ hp]
    have e : (T : ℝ) * a * (((k : ℝ) + 1) * (1 / 2 : ℝ) ^ (k + 1)) * 2 ^ (k + 1)
        = (T : ℝ) * a * ((k : ℝ) + 1) := by
      rw [one_div_pow]; field_simp
    rw [e]
    have h4 := hl4 k d
    have hk0 : (0 : ℝ) ≤ (k : ℝ) := Nat.cast_nonneg k
    have h5 : (T : ℝ) * (Real.log A + C₁) + (T : ℝ) * (8 + (k : ℝ)) ≤ (T : ℝ) * a * ((k : ℝ) + 1) := by
      have h6 : Real.log A + C₁ + (8 + (k : ℝ)) ≤ a * ((k : ℝ) + 1) := by
        have := mul_le_mul_of_nonneg_right ha1 hk0
        rw [ha] at this ⊢; nlinarith
      have := mul_le_mul_of_nonneg_left h6 hTR.le
      linarith
    exact h4.trans h5
  have hcard : (Finset.univ : Finset (Fin M → Fin 6)).card = 6 ^ M := by simp
  have htot : ∑ t ∈ Finset.range T,
      |Opn.E69.signedTail M P n₀ t - Opn.E69.signedTailBelow z M P n₀ t|
      ≤ (1 / 2 ^ (3 * M) : ℝ) * ((6 : ℝ) ^ M * ((T : ℝ) * a * S₀)) := by
    refine (Finset.sum_le_sum fun t _ => (hl5 t).2).trans ?_
    rw [← Finset.mul_sum, Finset.sum_comm]
    refine mul_le_mul_of_nonneg_left ?_ (by positivity)
    refine (Finset.sum_le_sum fun d _ => hline d).trans ?_
    rw [Finset.sum_const, hcard, nsmul_eq_mul]
    push_cast
    exact le_refl _
  rw [div_le_iff₀ hTR]
  refine htot.trans ?_
  have h34 : (1 / 2 ^ (3 * M) : ℝ) * (6 : ℝ) ^ M = (3 / 4 : ℝ) ^ M := by
    rw [pow_mul, one_div, ← inv_pow, ← mul_pow]; norm_num
  have hC : a * S₀ ≤ ((⌈S₀ * (C₁ + 8)⌉₊ + ⌈S₀⌉₊ : ℕ) : ℝ) * (1 + Real.log A) := by
    have h1 := Nat.le_ceil (S₀ * (C₁ + 8))
    have h2 := Nat.le_ceil S₀
    have h3 : S₀ * Real.log A ≤ (⌈S₀⌉₊ : ℝ) * Real.log A := mul_le_mul_of_nonneg_right h2 hlogA
    have h4 : (0 : ℝ) ≤ (⌈S₀ * (C₁ + 8)⌉₊ : ℝ) * Real.log A := by positivity
    have h5 : (0 : ℝ) ≤ (⌈S₀⌉₊ : ℝ) := Nat.cast_nonneg _
    rw [ha]; push_cast; nlinarith
  have h34pos : (0 : ℝ) ≤ (3 / 4 : ℝ) ^ M := by positivity
  calc (1 / 2 ^ (3 * M) : ℝ) * ((6 : ℝ) ^ M * ((T : ℝ) * a * S₀))
      = (3 / 4 : ℝ) ^ M * (a * S₀) * T := by rw [← h34]; ring
    _ ≤ (3 / 4 : ℝ) ^ M * (((⌈S₀ * (C₁ + 8)⌉₊ + ⌈S₀⌉₊ : ℕ) : ℝ) * (1 + Real.log A)) * T :=
        mul_le_mul_of_nonneg_right (mul_le_mul_of_nonneg_left hC h34pos) hTR.le
    _ = _ := by ring
