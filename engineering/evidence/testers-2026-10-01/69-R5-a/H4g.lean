import Mathlib
import Defs.Construction

/-- h4g (the parameters fit), proved (69-R5-a, 2026-10-01). Choice: `M = 2m` with `m` large,
`P = 2^(6^M D)` with `D > 8/η`, `z = modulus·6^M·2E + P^(2^(K·100^M))` with `E > 1/η`.
Then `log₂log₂log₂ z ≤ 7M + G` with `G` independent of `M`, so `log A = O(M)` and
`(3/4)^M · O(M) → 0`. -/
theorem erdos_69__h4__h7 : ∀ (C K K' : ℕ) (η : ℝ), 0 < η → ∃ M P z : ℕ, 0 < M ∧ Even M ∧ 2 ≤ P ∧ 7 ^ M ≤ P ∧
      (6 : ℝ) ^ M * (5 / Real.log P) < η ∧ 0 < z ∧ Opn.E69.modulus M P ≤ z ∧
      P ^ (2 ^ (K * 100 ^ M)) ≤ z ∧
      (∑ d : Fin M → Fin 6, ((Opn.E69.dil M P d).primeFactors.card : ℝ)) / (z : ℝ) < η ∧
      ∀ A : ℕ, 1 ≤ A → A ≤ K' * 100 ^ M * (1 + Nat.log 2 (Nat.log 2 (Nat.log 2 z))) →
        (C : ℝ) * (3 / 4 : ℝ) ^ M * (1 + Real.log A) ≤ η := by
  intro C K K' η hη
  have hself : ∀ n : ℕ, n ≤ 2 ^ n := fun n => Nat.lt_two_pow_self.le
  have hadd : ∀ x y i j : ℕ, x ≤ 2 ^ i → y ≤ 2 ^ j → x + y ≤ 2 ^ (i + j + 1) := by
    intro x y i j hx hy
    have h1 : 2 ^ i ≤ 2 ^ (i + j) := Nat.pow_le_pow_right (by norm_num) (by omega)
    have h2 : 2 ^ j ≤ 2 ^ (i + j) := Nat.pow_le_pow_right (by norm_num) (by omega)
    have h3 : 2 ^ (i + j + 1) = 2 * 2 ^ (i + j) := by rw [pow_succ]; ring
    omega
  have hmul : ∀ x y i j : ℕ, x ≤ 2 ^ i → y ≤ 2 ^ j → x * y ≤ 2 ^ (i + j) := by
    intro x y i j hx hy
    rw [pow_add]; exact Nat.mul_le_mul hx hy
  have hlog2 : ∀ x s : ℕ, x ≤ 2 ^ s → Nat.log 2 x ≤ s := by
    intro x s h
    exact (Nat.log_mono_right h).trans_eq (Nat.log_pow (by norm_num) s)
  -- constants
  obtain ⟨D, hD⟩ : ∃ D : ℕ, D = ⌈8 / η⌉₊ + 1 := ⟨_, rfl⟩
  obtain ⟨E, hE⟩ : ∃ E : ℕ, E = ⌈1 / η⌉₊ + 1 := ⟨_, rfl⟩
  have hDη : 8 < η * D := by
    have h := Nat.le_ceil (8 / η)
    rw [div_le_iff₀ hη] at h
    rw [hD]; push_cast; nlinarith
  have hEη : 1 < η * E := by
    have h := Nat.le_ceil (1 / η)
    rw [div_le_iff₀ hη] at h
    rw [hE]; push_cast; nlinarith
  have hD1 : 1 ≤ D := by omega
  obtain ⟨G, hG⟩ : ∃ G : ℕ, G = 2 * D + 2 * E + K + 15 := ⟨_, rfl⟩
  obtain ⟨c, hc⟩ : ∃ c : ℕ, c = K' + G + 2 := ⟨_, rfl⟩
  obtain ⟨m, hm⟩ : ∃ m : ℕ, m = ⌈9 * (C : ℝ) * ((c : ℝ) + 28) / η⌉₊ + 1 := ⟨_, rfl⟩
  have hm1 : 1 ≤ m := by omega
  have hmη : 9 * (C : ℝ) * ((c : ℝ) + 28) ≤ η * m := by
    have h := Nat.le_ceil (9 * (C : ℝ) * ((c : ℝ) + 28) / η)
    rw [div_le_iff₀ hη] at h
    rw [hm]; push_cast; nlinarith
  obtain ⟨M, hM⟩ : ∃ M : ℕ, M = 2 * m := ⟨_, rfl⟩
  have hM1 : 1 ≤ M := by omega
  obtain ⟨N, hN⟩ : ∃ N : ℕ, N = 6 ^ M * D := ⟨_, rfl⟩
  obtain ⟨P, hP⟩ : ∃ P : ℕ, P = 2 ^ N := ⟨_, rfl⟩
  obtain ⟨H, hH⟩ : ∃ H : ℕ, H = 100 ^ M := ⟨_, rfl⟩
  obtain ⟨Q, hQ⟩ : ∃ Q : ℕ, Q = 2 ^ (K * H) := ⟨_, rfl⟩
  obtain ⟨z, hz⟩ : ∃ z : ℕ, z = Opn.E69.modulus M P * (6 ^ M * (2 * E)) + P ^ Q := ⟨_, rfl⟩
  -- elementary size facts
  have h6pos : 1 ≤ 6 ^ M := Nat.one_le_pow _ _ (by norm_num)
  have hH1 : 1 ≤ H := by rw [hH]; exact Nat.one_le_pow _ _ (by norm_num)
  have hMH : M ≤ H := by
    rw [hH]; exact (hself M).trans (Nat.pow_le_pow_left (by norm_num) M)
  have h6H : 6 ^ M ≤ H := by rw [hH]; exact Nat.pow_le_pow_left (by norm_num) M
  have h68 : 6 ^ M ≤ 2 ^ (3 * M) := by
    rw [pow_mul]; exact Nat.pow_le_pow_left (by norm_num) M
  have hH2 : H ≤ 2 ^ (7 * M) := by
    rw [hH, pow_mul]; exact Nat.pow_le_pow_left (by norm_num) M
  have hN1 : 1 ≤ N := by rw [hN]; exact Nat.mul_pos h6pos hD1
  have h3MN : 3 * M ≤ N := by
    have h1 : 3 * M ≤ 6 ^ M := by
      have h2 : (3 : ℕ) ^ 1 ≤ 3 ^ M := Nat.pow_le_pow_right (by norm_num) hM1
      have h3 : (6 : ℕ) ^ M = 3 ^ M * 2 ^ M := by rw [← Nat.mul_pow]
      rw [h3]
      exact Nat.mul_le_mul (by simpa using h2) (hself M)
    rw [hN]; exact h1.trans (Nat.le_mul_of_pos_right _ hD1)
  have hP2 : 2 ≤ P := by
    rw [hP]; calc 2 = 2 ^ 1 := by norm_num
      _ ≤ 2 ^ N := Nat.pow_le_pow_right (by norm_num) hN1
  have hP7 : 7 ^ M ≤ P := by
    rw [hP]
    calc 7 ^ M ≤ 8 ^ M := Nat.pow_le_pow_left (by norm_num) M
      _ = 2 ^ (3 * M) := by rw [pow_mul]; norm_num
      _ ≤ 2 ^ N := Nat.pow_le_pow_right (by norm_num) h3MN
  -- the dilations and the modulus
  have hg : ∀ d : Fin M → Fin 6, Opn.E69.gIndex M d < 7 ^ M := by
    intro d
    have hdig : ∀ (r : ℕ) (k : Fin 6), Opn.E69.gDigit r k ≤ 6 := by
      intro r k
      unfold Opn.E69.gDigit
      split_ifs <;> fin_cases k <;> simp
    have h1 : Opn.E69.gIndex M d ≤ ∑ r : Fin M, 7 ^ (r : ℕ) * 6 :=
      Finset.sum_le_sum fun r _ => Nat.mul_le_mul_left _ (hdig r (d r))
    have h2 : ∑ r : Fin M, 7 ^ (r : ℕ) * 6 = ∑ r ∈ Finset.range M, 7 ^ r * 6 :=
      Fin.sum_univ_eq_sum_range (fun r => 7 ^ r * 6) M
    have h3 : ∀ n : ℕ, ∑ r ∈ Finset.range n, 7 ^ r * 6 + 1 = 7 ^ n := by
      intro n
      induction n with
      | zero => simp
      | succ n ih => rw [Finset.sum_range_succ, pow_succ]; omega
    have := h3 M
    omega
  have hdil : ∀ d : Fin M → Fin 6, Opn.E69.dil M P d ≤ 2 ^ (2 * P + 3 * M + 1) := by
    intro d
    have hpr : primorial P ≤ 4 ^ P := primorial_le_four_pow P
    have h78 : 7 ^ M ≤ 8 ^ M := Nat.pow_le_pow_left (by norm_num) M
    have h1 : primorial P * (1 + Opn.E69.gIndex M d) ≤ 4 ^ P * 8 ^ M :=
      Nat.mul_le_mul hpr (by have := hg d; omega)
    have h2 : 1 ≤ 4 ^ P * 8 ^ M :=
      Nat.mul_pos (Nat.pos_of_ne_zero (by positivity)) (Nat.pos_of_ne_zero (by positivity))
    have h3 : 2 ^ (2 * P + 3 * M + 1) = 2 * (4 ^ P * 8 ^ M) := by
      rw [pow_succ, pow_add, pow_mul, pow_mul]; norm_num; ring
    unfold Opn.E69.dil
    rw [h3]; omega
  have hcard : (Finset.univ : Finset (Fin M → Fin 6)).card = 6 ^ M := by simp
  have hmodpos : 0 < Opn.E69.modulus M P := by
    unfold Opn.E69.modulus
    exact Finset.prod_pos fun d _ => by unfold Opn.E69.dil; omega
  have hmod : Opn.E69.modulus M P ≤ 2 ^ ((2 * P + 3 * M + 1) * 6 ^ M) := by
    have h := Finset.prod_le_pow_card (Finset.univ : Finset (Fin M → Fin 6))
      (fun d => Opn.E69.dil M P d) _ (fun d _ => hdil d)
    rw [hcard, ← pow_mul] at h
    exact h
  have hdilmod : ∀ d : Fin M → Fin 6, Opn.E69.dil M P d ≤ Opn.E69.modulus M P := fun d =>
    Nat.le_of_dvd hmodpos (Finset.dvd_prod_of_mem _ (Finset.mem_univ d))
  have hpf : ∀ n : ℕ, n.primeFactors.card ≤ n := by
    intro n
    have hsub : n.primeFactors ⊆ Finset.Icc 1 n := by
      intro p hp
      rw [Finset.mem_Icc]
      exact ⟨(Nat.prime_of_mem_primeFactors hp).pos, Nat.le_of_mem_primeFactors hp⟩
    have := Finset.card_le_card hsub
    simpa using this
  -- size of z
  have hzpos : 0 < z := by
    rw [hz]
    have : 0 < P ^ Q := Nat.pos_of_ne_zero (pow_ne_zero _ (by omega))
    omega
  have hzmod : Opn.E69.modulus M P ≤ z := by
    rw [hz]
    have : Opn.E69.modulus M P * 1 ≤ Opn.E69.modulus M P * (6 ^ M * (2 * E)) :=
      Nat.mul_le_mul_left _ (Nat.mul_pos h6pos (by omega))
    omega
  have hzQ : P ^ Q ≤ z := by rw [hz]; omega
  have hPQ : P ^ Q = 2 ^ (N * Q) := by rw [hP, pow_mul]
  have hzle : z ≤ 2 ^ ((2 * P + 3 * M + 1) * 6 ^ M + (3 * M + 2 * E) + N * Q + 1) := by
    rw [hz]
    refine hadd _ _ _ _ ?_ (le_of_eq hPQ)
    exact hmul _ _ _ _ hmod (hmul _ _ _ _ h68 (hself _))
  have hL1 : Nat.log 2 z ≤ (2 * P + 3 * M + 1) * 6 ^ M + (3 * M + 2 * E) + N * Q + 1 :=
    hlog2 _ _ hzle
  have he : 2 * P + 3 * M + 1 ≤ 2 ^ (N + 1 + (3 * M + 1) + 1) := by
    have h2P : 2 * P ≤ 2 ^ (N + 1) := by rw [hP, pow_succ]; omega
    have := hadd _ _ _ _ h2P (hself (3 * M + 1))
    omega
  have hL1' : (2 * P + 3 * M + 1) * 6 ^ M + (3 * M + 2 * E) + N * Q + 1
      ≤ 2 ^ ((N + 1 + (3 * M + 1) + 1 + 3 * M) + (3 * M + 2 * E) + 1 + (N + K * H) + 1 + 0 + 1) := by
    refine hadd _ 1 _ 0 (hadd _ _ _ _ (hadd _ _ _ _ (hmul _ _ _ _ he h68) (hself _)) ?_) (by norm_num)
    exact hmul _ _ _ _ (hself N) (le_of_eq hQ)
  have hL2 : Nat.log 2 (Nat.log 2 z)
      ≤ (N + 1 + (3 * M + 1) + 1 + 3 * M) + (3 * M + 2 * E) + 1 + (N + K * H) + 1 + 0 + 1 :=
    hlog2 _ _ (hL1.trans hL1')
  have hS : (N + 1 + (3 * M + 1) + 1 + 3 * M) + (3 * M + 2 * E) + 1 + (N + K * H) + 1 + 0 + 1
      ≤ 2 ^ (7 * M + G) := by
    have hND : N ≤ H * D := by rw [hN]; exact Nat.mul_le_mul_right D h6H
    have hEH : E ≤ H * E := Nat.le_mul_of_pos_left E hH1
    have h1 : (N + 1 + (3 * M + 1) + 1 + 3 * M) + (3 * M + 2 * E) + 1 + (N + K * H) + 1 + 0 + 1
        ≤ H * G := by
      have h2 : H * G = 2 * (H * D) + 2 * (H * E) + K * H + 15 * H := by rw [hG]; ring
      rw [h2]; omega
    exact h1.trans (hmul _ _ _ _ hH2 (hself G))
  have hL3 : Nat.log 2 (Nat.log 2 (Nat.log 2 z)) ≤ 7 * M + G := hlog2 _ _ (hL2.trans hS)
  -- the decay of (3/4)^M
  have hX : (3 / 4 : ℝ) ^ M * (m : ℝ) ^ 2 ≤ 9 := by
    have hb : 1 + (m : ℝ) * (1 / 3) ≤ (1 + 1 / 3 : ℝ) ^ m :=
      one_add_mul_le_pow (by norm_num) m
    have hb' : (m : ℝ) ≤ 3 * (4 / 3 : ℝ) ^ m := by
      have e : (1 + 1 / 3 : ℝ) = 4 / 3 := by norm_num
      rw [e] at hb; linarith
    have hm0 : (0 : ℝ) ≤ m := Nat.cast_nonneg m
    have hsq : (m : ℝ) ^ 2 ≤ 9 * ((4 / 3 : ℝ) ^ m) ^ 2 := by nlinarith
    have hone : (3 / 4 : ℝ) ^ M * ((4 / 3 : ℝ) ^ m) ^ 2 = 1 := by
      rw [hM, ← pow_mul, mul_comm m 2, ← mul_pow]; norm_num
    have hpos : (0 : ℝ) ≤ (3 / 4 : ℝ) ^ M := by positivity
    calc (3 / 4 : ℝ) ^ M * (m : ℝ) ^ 2 ≤ (3 / 4 : ℝ) ^ M * (9 * ((4 / 3 : ℝ) ^ m) ^ 2) :=
          mul_le_mul_of_nonneg_left hsq hpos
      _ = 9 * ((3 / 4 : ℝ) ^ M * ((4 / 3 : ℝ) ^ m) ^ 2) := by ring
      _ = 9 := by rw [hone]; norm_num
  refine ⟨M, P, z, hM1, ⟨m, by omega⟩, hP2, hP7, ?_, hzpos, hzmod, ?_, ?_, ?_⟩
  · -- the reciprocal budget
    have hl2 : (0.69 : ℝ) < Real.log 2 := by linarith [Real.log_two_gt_d9]
    have hlogP : Real.log (P : ℝ) = (6 : ℝ) ^ M * D * Real.log 2 := by
      rw [hP, hN]; push_cast; rw [Real.log_pow]; push_cast; ring
    have h6 : (0 : ℝ) < (6 : ℝ) ^ M := by positivity
    have hDp : (0 : ℝ) < (D : ℝ) := by exact_mod_cast hD1
    have hden : (0 : ℝ) < (D : ℝ) * Real.log 2 := by positivity
    have e : (6 : ℝ) ^ M * (5 / Real.log P) = 5 / ((D : ℝ) * Real.log 2) := by
      rw [hlogP]; field_simp
    rw [e, div_lt_iff₀ hden]
    nlinarith
  · rw [hH] at hQ; rw [← hQ]; exact hzQ
  · -- the cardinality budget
    have hzR : (0 : ℝ) < (z : ℝ) := by exact_mod_cast hzpos
    rw [div_lt_iff₀ hzR]
    have h1 : ∑ d : Fin M → Fin 6, ((Opn.E69.dil M P d).primeFactors.card : ℝ)
        ≤ ∑ _d : Fin M → Fin 6, (Opn.E69.modulus M P : ℝ) :=
      Finset.sum_le_sum fun d _ => by exact_mod_cast (hpf _).trans (hdilmod d)
    rw [Finset.sum_const, hcard, nsmul_eq_mul] at h1
    have hW : (0 : ℝ) < ((6 ^ M : ℕ) : ℝ) * (Opn.E69.modulus M P : ℝ) := by
      have : 0 < 6 ^ M * Opn.E69.modulus M P := Nat.mul_pos h6pos hmodpos
      exact_mod_cast this
    have hzW : ((6 ^ M : ℕ) : ℝ) * (Opn.E69.modulus M P : ℝ) * (2 * E) ≤ (z : ℝ) := by
      have : 6 ^ M * Opn.E69.modulus M P * (2 * E) ≤ z := by
        rw [hz]
        have : 6 ^ M * Opn.E69.modulus M P * (2 * E)
            = Opn.E69.modulus M P * (6 ^ M * (2 * E)) := by ring
        omega
      exact_mod_cast this
    have h3 : ((6 ^ M : ℕ) : ℝ) * (Opn.E69.modulus M P : ℝ)
        < η * (((6 ^ M : ℕ) : ℝ) * (Opn.E69.modulus M P : ℝ) * (2 * E)) := by nlinarith
    have h4 : η * (((6 ^ M : ℕ) : ℝ) * (Opn.E69.modulus M P : ℝ) * (2 * E)) ≤ η * z :=
      mul_le_mul_of_nonneg_left hzW hη.le
    linarith
  · intro A hA1 hA
    have hA2 : A ≤ 2 ^ (K' + 7 * M + (7 * M + G + 1)) := by
      refine hA.trans (hmul _ _ _ _ (hmul _ _ _ _ (hself K') (hH ▸ hH2)) ?_)
      have := hself (7 * M + G + 1)
      omega
    have hAR : (A : ℝ) ≤ (2 : ℝ) ^ (K' + 7 * M + (7 * M + G + 1)) := by exact_mod_cast hA2
    have hApos : (0 : ℝ) < (A : ℝ) := by exact_mod_cast hA1
    have hlogA : Real.log A ≤ ((K' + 7 * M + (7 * M + G + 1) : ℕ) : ℝ) := by
      have h1 := Real.log_le_log hApos hAR
      rw [Real.log_pow] at h1
      have hl2 : Real.log 2 ≤ 1 := by linarith [Real.log_two_lt_d9]
      have hn : (0 : ℝ) ≤ ((K' + 7 * M + (7 * M + G + 1) : ℕ) : ℝ) := Nat.cast_nonneg _
      have := mul_le_mul_of_nonneg_left hl2 hn
      linarith
    have hm0 : (0 : ℝ) < (m : ℝ) := by exact_mod_cast hm1
    have hm1R : (1 : ℝ) ≤ (m : ℝ) := by exact_mod_cast hm1
    have hB : 1 + Real.log A ≤ ((c : ℝ) + 28) * m := by
      have e : ((K' + 7 * M + (7 * M + G + 1) : ℕ) : ℝ) = (c : ℝ) - 1 + 28 * m := by
        rw [hc, hM]; push_cast; ring
      rw [e] at hlogA
      have hc0 : (0 : ℝ) ≤ (c : ℝ) := Nat.cast_nonneg c
      have hcm : (c : ℝ) * 1 ≤ (c : ℝ) * m := mul_le_mul_of_nonneg_left hm1R hc0
      linarith
    have hXpos : (0 : ℝ) ≤ (3 / 4 : ℝ) ^ M := by positivity
    have hC0 : (0 : ℝ) ≤ (C : ℝ) := Nat.cast_nonneg C
    have hCX : (0 : ℝ) ≤ (C : ℝ) * (3 / 4 : ℝ) ^ M := mul_nonneg hC0 hXpos
    have h1 : (C : ℝ) * (3 / 4 : ℝ) ^ M * (1 + Real.log A)
        ≤ (C : ℝ) * (3 / 4 : ℝ) ^ M * (((c : ℝ) + 28) * m) := mul_le_mul_of_nonneg_left hB hCX
    refine le_of_mul_le_mul_right ?_ hm0
    have hc28 : (0 : ℝ) ≤ (C : ℝ) * ((c : ℝ) + 28) := by positivity
    have h2 : (C : ℝ) * (3 / 4 : ℝ) ^ M * (((c : ℝ) + 28) * m) * m
        = (C : ℝ) * ((c : ℝ) + 28) * ((3 / 4 : ℝ) ^ M * (m : ℝ) ^ 2) := by ring
    have h3 : (C : ℝ) * ((c : ℝ) + 28) * ((3 / 4 : ℝ) ^ M * (m : ℝ) ^ 2)
        ≤ (C : ℝ) * ((c : ℝ) + 28) * 9 := mul_le_mul_of_nonneg_left hX hc28
    have h4 : (C : ℝ) * (3 / 4 : ℝ) ^ M * (1 + Real.log A) * m
        ≤ (C : ℝ) * (3 / 4 : ℝ) ^ M * (((c : ℝ) + 28) * m) * m :=
      mul_le_mul_of_nonneg_right h1 hm0.le
    linarith
