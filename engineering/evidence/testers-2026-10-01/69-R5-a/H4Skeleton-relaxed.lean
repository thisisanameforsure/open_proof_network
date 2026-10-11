import Mathlib
import Defs.Construction

open scoped ArithmeticFunction.omega

/-! RELAXED h4e/h4g variant (69-R5-a): A may be as large as K'·100^M·(1 + log₂log₂ z)². Second-layer skeleton for hole h4 of the erdos-69 root skeleton (69-R4-b, 2026-10-01), over
`Defs.Construction` v2. h4 is proved from seven holes: the six of 69-R3-b/H4-VERDICT.md and one
parameter-choice hole (h4g, elementary real arithmetic) that keeps the assembly short.
h4a, h4b, h4c are proved in H4a.lean, H4b.lean, H4c.lean. -/

theorem erdos_69__h4 : ∀ (q : ℕ), 0 < q → ∀ ε : ℝ, 0 < ε →
    ∃ M P T : ℕ, 2 ≤ P ∧ 7 ^ M ≤ P ∧ 0 < T ∧
      (6 : ℝ) ^ M * (5 / Real.log P) < ε ∧
      (∑ d : Fin M → Fin 6, ((Opn.E69.dil M P d).primeFactors.card : ℝ)) / T < ε ∧
      ∀ n₀ : ℕ, n₀ < Opn.E69.modulus M P → Opn.E69.Admissible M P n₀ →
        ‖Opn.E69.charMean q M P n₀ T‖ < ε := by
  -- h4a (exact cancellation; elementary, PROVED in H4a.lean)
  have h4a : ∀ (M P u x : ℕ), Even M → 1 ≤ u → u ≤ 3 * M →
      ∑ d ∈ Finset.univ.filter (fun d : Fin M → Fin 6 =>
        Opn.E69.shift M P d + Opn.E69.dil M P d * u = x), Opn.E69.sign M d = 0 := by
    sorry
  -- h4b (what is left is 2^(-3M) of later tails; elementary, PROVED in H4b.lean)
  have h4b : ∀ (M P n₀ t : ℕ), Even M → Opn.E69.Admissible M P n₀ →
      (Opn.E69.signedTail M P n₀ t = (1 / 2 ^ (3 * M) : ℝ) *
        ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) * Opn.E69.tail (Opn.E69.dil M P d)
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M)) ∧
      ∀ z : ℕ, Opn.E69.signedTailBelow z M P n₀ t = (1 / 2 ^ (3 * M) : ℝ) *
        ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) * Opn.E69.tailBelow z (Opn.E69.dil M P d)
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t + 3 * M) := by
    sorry
  -- h4c (something survives: below depth 3M the line `2…2` is alone on its point at every
  -- depth; elementary, PROVED in H4c.lean). Feeds h4f: it is why the model does not degenerate.
  have h4c : ∀ (M P u : ℕ), Even M → 3 * M + 1 ≤ u → ∀ d : Fin M → Fin 6,
      Opn.E69.shift M P d + Opn.E69.dil M P d * u
        = Opn.E69.shift M P (fun _ => 2) + Opn.E69.dil M P (fun _ => 2) * u → d = fun _ => 2 := by
    sorry
  -- h4d (large primes; needs Mertens, node spec-7d098d5c): cutting ω at z costs, in mean over
  -- t < z^A, at most the surviving mass (3/4)^M times O(1 + log A).
  have h4d : ∃ C : ℕ, ∀ (M P z A n₀ : ℕ), Even M → 2 ≤ P → 7 ^ M ≤ P →
      Opn.E69.modulus M P ≤ z → 1 ≤ A → n₀ < Opn.E69.modulus M P → Opn.E69.Admissible M P n₀ →
      (∑ t ∈ Finset.range (z ^ A),
          |Opn.E69.signedTail M P n₀ t - Opn.E69.signedTailBelow z M P n₀ t|) / ((z ^ A : ℕ) : ℝ)
        ≤ (C : ℝ) * (3 / 4 : ℝ) ^ M * (1 + Real.log A) := by
    sorry
  -- h4e (small primes behave independently; a multi-shift fundamental lemma of sieve theory,
  -- analytic input Mathlib lacks): the mean over t < z^A is within η of the mean over a full
  -- period, for some A of size at most K'·100^M·(1 + log log log z).
  have h4e : ∀ (q : ℕ), 0 < q → ∀ η : ℝ, 0 < η → ∃ K' : ℕ, ∀ (M P z : ℕ), Even M → 0 < M →
      2 ≤ P → 7 ^ M ≤ P → Opn.E69.modulus M P ≤ z →
      ∃ A : ℕ, 1 ≤ A ∧ A ≤ K' * 100 ^ M * (1 + Nat.log 2 (Nat.log 2 z)) ^ 2 ∧
        ∀ n₀ : ℕ, n₀ < Opn.E69.modulus M P → Opn.E69.Admissible M P n₀ →
          ‖Opn.E69.charMeanBelow q z M P n₀ (z ^ A)
            - Opn.E69.charMeanBelow q z M P n₀ (primorial z)‖ ≤ η := by
    sorry
  -- h4f (the model decays; exact product over primes by the Chinese remainder theorem, then
  -- divergence of ∑ 1/p from spec-7d098d5c and a lower bound on each local factor from h4c).
  have h4f : ∀ (q : ℕ), 0 < q → ∀ η : ℝ, 0 < η → ∃ K : ℕ, ∀ (M P z : ℕ), Even M → 0 < M →
      2 ≤ P → 7 ^ M ≤ P → Opn.E69.modulus M P ≤ z → P ^ (2 ^ (K * 100 ^ M)) ≤ z →
      ∀ n₀ : ℕ, n₀ < Opn.E69.modulus M P → Opn.E69.Admissible M P n₀ →
        ‖Opn.E69.charMeanBelow q z M P n₀ (primorial z)‖ ≤ η := by
    sorry
  -- h4g (the parameters fit; elementary real arithmetic, no ω)
  have h4g : ∀ (C K K' : ℕ) (η : ℝ), 0 < η → ∃ M P z : ℕ, 0 < M ∧ Even M ∧ 2 ≤ P ∧ 7 ^ M ≤ P ∧
      (6 : ℝ) ^ M * (5 / Real.log P) < η ∧ 0 < z ∧ Opn.E69.modulus M P ≤ z ∧
      P ^ (2 ^ (K * 100 ^ M)) ≤ z ∧
      (∑ d : Fin M → Fin 6, ((Opn.E69.dil M P d).primeFactors.card : ℝ)) / (z : ℝ) < η ∧
      ∀ A : ℕ, 1 ≤ A → A ≤ K' * 100 ^ M * (1 + Nat.log 2 (Nat.log 2 z)) ^ 2 →
        (C : ℝ) * (3 / 4 : ℝ) ^ M * (1 + Real.log A) ≤ η := by
    sorry
  -- assembly
  intro q hq ε hε
  have hη : (0 : ℝ) < ε / 4 := by positivity
  obtain ⟨C, hd⟩ := h4d
  obtain ⟨K', he⟩ := h4e q hq (ε / 4) hη
  obtain ⟨K, hf⟩ := h4f q hq (ε / 4) hη
  obtain ⟨M, P, z, hM0, hMe, hP2, hP7, hlog, hz0, hzmod, hzK, hcard, hA⟩ :=
    h4g (7 * q * C) K K' (ε / 4) hη
  obtain ⟨A, hA1, hAle, hcmp⟩ := he M P z hMe hM0 hP2 hP7 hzmod
  have hzR : (0 : ℝ) < (z : ℝ) := by exact_mod_cast hz0
  have hTpos : 0 < z ^ A := Nat.pos_of_ne_zero (pow_ne_zero _ hz0.ne')
  have hTR : (0 : ℝ) < ((z ^ A : ℕ) : ℝ) := by exact_mod_cast hTpos
  have hzT : (z : ℝ) ≤ ((z ^ A : ℕ) : ℝ) := by
    have : z ≤ z ^ A := Nat.le_self_pow (by omega) z
    exact_mod_cast this
  refine ⟨M, P, z ^ A, hP2, hP7, hTpos, by linarith, ?_, ?_⟩
  · have hnn : (0 : ℝ) ≤ ∑ d : Fin M → Fin 6, ((Opn.E69.dil M P d).primeFactors.card : ℝ) :=
      Finset.sum_nonneg fun d _ => Nat.cast_nonneg _
    have := div_le_div_of_nonneg_left hnn hzR hzT
    linarith
  · intro n₀ hn₀ hadm
    -- two phases differ by at most 2π times the difference of the angles
    have hexp : ∀ x y : ℝ, ‖Complex.exp (2 * Real.pi * Complex.I * (x : ℂ))
        - Complex.exp (2 * Real.pi * Complex.I * (y : ℂ))‖ ≤ 2 * Real.pi * |x - y| := by
      intro x y
      have e1 : Complex.exp (2 * Real.pi * Complex.I * (x : ℂ))
          = Complex.exp (((2 * Real.pi * y : ℝ) : ℂ) * Complex.I)
            * Complex.exp (Complex.I * ((2 * Real.pi * (x - y) : ℝ) : ℂ)) := by
        rw [← Complex.exp_add]; congr 1; push_cast; ring
      have e2 : Complex.exp (2 * Real.pi * Complex.I * (y : ℂ))
          = Complex.exp (((2 * Real.pi * y : ℝ) : ℂ) * Complex.I) := by
        congr 1; push_cast; ring
      rw [e1, e2, ← mul_sub_one, norm_mul, Complex.norm_exp_ofReal_mul_I, one_mul]
      refine le_trans Real.norm_exp_I_mul_ofReal_sub_one_le ?_
      rw [Real.norm_eq_abs, abs_mul, abs_of_pos Real.two_pi_pos]
    have hqR : (0 : ℝ) ≤ (q : ℝ) := Nat.cast_nonneg q
    have h1 : ‖Opn.E69.charMean q M P n₀ (z ^ A) - Opn.E69.charMeanBelow q z M P n₀ (z ^ A)‖
        ≤ 2 * Real.pi * ((q : ℝ) * ((∑ t ∈ Finset.range (z ^ A),
          |Opn.E69.signedTail M P n₀ t - Opn.E69.signedTailBelow z M P n₀ t|)
            / ((z ^ A : ℕ) : ℝ))) := by
      unfold Opn.E69.charMean Opn.E69.charMeanBelow
      rw [← sub_div, ← Finset.sum_sub_distrib, norm_div, Complex.norm_natCast]
      calc _ ≤ (∑ t ∈ Finset.range (z ^ A), 2 * Real.pi * ((q : ℝ) *
              |Opn.E69.signedTail M P n₀ t - Opn.E69.signedTailBelow z M P n₀ t|))
                / ((z ^ A : ℕ) : ℝ) := by
            refine div_le_div_of_nonneg_right ?_ hTR.le
            refine le_trans (norm_sum_le _ _) (Finset.sum_le_sum fun t _ => ?_)
            refine le_trans (hexp _ _) ?_
            rw [← mul_sub, abs_mul, abs_of_nonneg hqR]
        _ = _ := by
            rw [← Finset.mul_sum, ← Finset.mul_sum]; ring
    have h2 := hd M P z A n₀ hMe hP2 hP7 hzmod hA1 hn₀ hadm
    have h3 := hA A hA1 hAle
    have h4 := hcmp n₀ hn₀ hadm
    have h5 := hf M P z hMe hM0 hP2 hP7 hzmod hzK n₀ hn₀ hadm
    have hπ : 2 * Real.pi ≤ 7 := by linarith [Real.pi_lt_d2]
    have hB : (0 : ℝ) ≤ (C : ℝ) * (3 / 4 : ℝ) ^ M * (1 + Real.log A) := by
      have : (0 : ℝ) ≤ Real.log A := Real.log_natCast_nonneg A
      positivity
    have h6 : 2 * Real.pi * ((q : ℝ) * ((∑ t ∈ Finset.range (z ^ A),
          |Opn.E69.signedTail M P n₀ t - Opn.E69.signedTailBelow z M P n₀ t|)
            / ((z ^ A : ℕ) : ℝ))) ≤ ε / 4 := by
      have h7 : (q : ℝ) * ((∑ t ∈ Finset.range (z ^ A),
          |Opn.E69.signedTail M P n₀ t - Opn.E69.signedTailBelow z M P n₀ t|)
            / ((z ^ A : ℕ) : ℝ)) ≤ (q : ℝ) * ((C : ℝ) * (3 / 4 : ℝ) ^ M * (1 + Real.log A)) :=
        mul_le_mul_of_nonneg_left h2 hqR
      have h8 : (((7 * q * C : ℕ) : ℝ)) * (3 / 4 : ℝ) ^ M * (1 + Real.log A)
          = 7 * ((q : ℝ) * ((C : ℝ) * (3 / 4 : ℝ) ^ M * (1 + Real.log A))) := by
        push_cast; ring
      have h9 : (0 : ℝ) ≤ (q : ℝ) * ((C : ℝ) * (3 / 4 : ℝ) ^ M * (1 + Real.log A)) :=
        mul_nonneg hqR hB
      rw [h8] at h3
      nlinarith [Real.pi_pos]
    have hn : ‖Opn.E69.charMean q M P n₀ (z ^ A)‖
        ≤ ‖Opn.E69.charMean q M P n₀ (z ^ A) - Opn.E69.charMeanBelow q z M P n₀ (z ^ A)‖
          + ‖Opn.E69.charMeanBelow q z M P n₀ (z ^ A)
              - Opn.E69.charMeanBelow q z M P n₀ (primorial z)‖
          + ‖Opn.E69.charMeanBelow q z M P n₀ (primorial z)‖ := by
      have e : Opn.E69.charMean q M P n₀ (z ^ A)
          = (Opn.E69.charMean q M P n₀ (z ^ A) - Opn.E69.charMeanBelow q z M P n₀ (z ^ A))
            + (Opn.E69.charMeanBelow q z M P n₀ (z ^ A)
              - Opn.E69.charMeanBelow q z M P n₀ (primorial z))
            + Opn.E69.charMeanBelow q z M P n₀ (primorial z) := by ring
      calc _ = ‖_‖ := by rw [← e]
        _ ≤ _ := norm_add₃_le
    linarith
