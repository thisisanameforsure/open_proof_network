import Mathlib
import Defs.Construction

open scoped ArithmeticFunction.omega

/-! Draft root skeleton for erdos-69 over `Defs.Construction` (69-R2-b, 2026-10-01).
Proved nodes cited (restated here with `sorry`, as a node Context does): `spec-9f8cb4ea` is not
needed by the assembly (it is inside `spec-84446025`); `spec-e0b917d1`; `spec-84446025`.
Holes h1..h4 are the new lemmas. -/

-- proved node spec-e0b917d1
theorem Opn.erdos_69_rough_dilation_reciprocal :
    ∀ P j : ℕ, 2 ≤ P → j ≤ P →
      ∑ p ∈ (1 + primorial P * (1 + j)).primeFactors, (1 : ℝ) / p ≤ 5 / Real.log P := by
  sorry

-- proved node spec-84446025
theorem Opn.erdos_69_rational_dilated_tails_near_integers :
    ∀ (q : ℕ) (z : ℤ), (q : ℝ) * ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = z →
      ∀ (a Q b T : ℕ), a ≠ 0 → 0 < T → (∀ p ∈ a.primeFactors, Nat.Coprime p Q) →
        (∑ t ∈ Finset.range T,
            |(q : ℝ) * ∑' k : ℕ, (ω (a * (b + Q * t + (k + 1))) : ℝ) / 2 ^ (k + 1)
              - round ((q : ℝ) * ∑' k : ℕ, (ω (a * (b + Q * t + (k + 1))) : ℝ) / 2 ^ (k + 1))|) / T
          ≤ (q : ℝ) * ∑ p ∈ a.primeFactors, ((1 : ℝ) / p + 1 / T) := by
  sorry

/-- h1 (digits): the slope index is a base-7 number below `7^M`. -/
theorem erdos_69__h1 : ∀ (M : ℕ) (d : Fin M → Fin 6), Opn.E69.gIndex M d < 7 ^ M := by
  sorry

/-- h2 (coprimality): for `7^M ≤ P` every prime factor of a dilation is coprime to its step. -/
theorem erdos_69__h2 : ∀ (M P : ℕ), 7 ^ M ≤ P → ∀ (d : Fin M → Fin 6),
    ∀ p ∈ (Opn.E69.dil M P d).primeFactors, Nat.Coprime p (Opn.E69.step M P d) := by
  sorry

/-- h3 (the construction exists): the Chinese-remainder system has a solution below the modulus. -/
theorem erdos_69__h3 : ∀ (M P : ℕ), 7 ^ M ≤ P →
    ∃ n₀ : ℕ, n₀ < Opn.E69.modulus M P ∧ Opn.E69.Admissible M P n₀ := by
  sorry

/-- h4 (decay; the theorem): unconditionally, for every `q ≥ 1` and `ε > 0` there are parameters
at which the correction budget is below `ε` and the characteristic function of `q ·` the signed
combination has mean below `ε` in absolute value, from every base point. -/
theorem erdos_69__h4 : ∀ (q : ℕ), 0 < q → ∀ ε : ℝ, 0 < ε →
    ∃ M P T : ℕ, 2 ≤ P ∧ 7 ^ M ≤ P ∧ 0 < T ∧
      (6 : ℝ) ^ M * (5 / Real.log P) < ε ∧
      (∑ d : Fin M → Fin 6, ((Opn.E69.dil M P d).primeFactors.card : ℝ)) / T < ε ∧
      ∀ n₀ : ℕ, n₀ < Opn.E69.modulus M P → Opn.E69.Admissible M P n₀ →
        ‖Opn.E69.charMean q M P n₀ T‖ < ε := by
  sorry

theorem Opn.erdos_69 :
    Irrational <| ∑' n, ω (n + 2) / 2 ^ (n + 2) := by
  rintro ⟨r, hr⟩
  have hX : ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = ∑' n : ℕ, (ω (n + 2) : ℝ) / 2 ^ (n + 2) := by
    by_cases hs : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n)
    · rw [← hs.sum_add_tsum_nat_add 2]
      simp [Finset.sum_range_succ]
    · rw [tsum_eq_zero_of_not_summable hs,
        tsum_eq_zero_of_not_summable (mt (summable_nat_add_iff 2).1 hs)]
  have hqz : (r.den : ℝ) * ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = (r.num : ℤ) := by
    rw [hX, ← hr]
    have h := Rat.mul_den_eq_num r
    have h' : (r : ℝ) * (r.den : ℝ) = (r.num : ℝ) := by exact_mod_cast h
    linarith
  set q : ℕ := r.den with hq
  have hqpos : 0 < q := r.den_pos
  have hqR : (0 : ℝ) < q := by exact_mod_cast hqpos
  set ε : ℝ := 1 / (2 + 26 * (q : ℝ)) with hε
  have hεpos : 0 < ε := by positivity
  obtain ⟨M, P, T, hP2, hP7, hT, hlog, hcard, hdec⟩ := erdos_69__h4 q hqpos ε hεpos
  obtain ⟨n₀, hn₀, hadm⟩ := erdos_69__h3 M P hP7
  have hdecay := hdec n₀ hn₀ hadm
  have hTR : (0 : ℝ) < T := by exact_mod_cast hT
  -- the distance of `q · tail_d(t)` to the integers
  set δ : (Fin M → Fin 6) → ℕ → ℝ := fun d t =>
    |(q : ℝ) * Opn.E69.tail (Opn.E69.dil M P d) (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t)
      - round ((q : ℝ) * Opn.E69.tail (Opn.E69.dil M P d)
          (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t))| with hδ
  -- rational side, one line at a time (spec-84446025, spec-e0b917d1, h1, h2)
  have hline : ∀ d : Fin M → Fin 6, (∑ t ∈ Finset.range T, δ d t) / T
      ≤ (q : ℝ) * (5 / Real.log P + ((Opn.E69.dil M P d).primeFactors.card : ℝ) / T) := by
    intro d
    have h := Opn.erdos_69_rational_dilated_tails_near_integers q r.num hqz
      (Opn.E69.dil M P d) (Opn.E69.step M P d) (Opn.E69.start M P n₀ d) T
      (by unfold Opn.E69.dil; omega) hT (erdos_69__h2 M P hP7 d)
    have hr5 := Opn.erdos_69_rough_dilation_reciprocal P (Opn.E69.gIndex M d) hP2
      (le_trans (erdos_69__h1 M d).le hP7)
    refine le_trans h (mul_le_mul_of_nonneg_left ?_ hqR.le)
    rw [Finset.sum_add_distrib, Finset.sum_const, nsmul_eq_mul]
    have : ∑ p ∈ (Opn.E69.dil M P d).primeFactors, (1 : ℝ) / p ≤ 5 / Real.log P := hr5
    have e : ((Opn.E69.dil M P d).primeFactors.card : ℝ) * (1 / (T : ℝ))
        = ((Opn.E69.dil M P d).primeFactors.card : ℝ) / T := by ring
    linarith
  -- pointwise: the phase is within `2π ∑_d δ` of 1
  have hpt : ∀ t : ℕ, ‖Complex.exp (2 * Real.pi * Complex.I *
      (((q : ℝ) * Opn.E69.signedTail M P n₀ t : ℝ) : ℂ)) - 1‖
      ≤ 2 * Real.pi * ∑ d : Fin M → Fin 6, δ d t := by
    intro t
    set τ : (Fin M → Fin 6) → ℝ := fun d => (q : ℝ) * Opn.E69.tail (Opn.E69.dil M P d)
      (Opn.E69.start M P n₀ d + Opn.E69.step M P d * t) with hτ
    have hθ : (q : ℝ) * Opn.E69.signedTail M P n₀ t
        = ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) * τ d := by
      unfold Opn.E69.signedTail
      rw [Finset.mul_sum]
      refine Finset.sum_congr rfl fun d _ => ?_
      rw [hτ]; ring
    set k : ℤ := ∑ d : Fin M → Fin 6, Opn.E69.sign M d * round (τ d) with hk
    set v : ℝ := 2 * Real.pi * (∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) * τ d - k) with hv
    have hexp : Complex.exp (2 * Real.pi * Complex.I *
        (((q : ℝ) * Opn.E69.signedTail M P n₀ t : ℝ) : ℂ)) = Complex.exp (Complex.I * (v : ℂ)) := by
      rw [hθ]
      have e : 2 * (Real.pi : ℂ) * Complex.I *
          ((∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) * τ d : ℝ) : ℂ)
          = Complex.I * (v : ℂ) + (k : ℂ) * (2 * Real.pi * Complex.I) := by
        rw [hv]; push_cast; ring
      rw [e, Complex.exp_add, Complex.exp_int_mul_two_pi_mul_I, mul_one]
    rw [hexp]
    refine le_trans Real.norm_exp_I_mul_ofReal_sub_one_le ?_
    rw [Real.norm_eq_abs, hv, abs_mul, abs_of_pos Real.two_pi_pos]
    refine mul_le_mul_of_nonneg_left ?_ Real.two_pi_pos.le
    have e2 : ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) * τ d - (k : ℝ)
        = ∑ d : Fin M → Fin 6, (Opn.E69.sign M d : ℝ) * (τ d - round (τ d)) := by
      rw [hk]; push_cast; rw [← Finset.sum_sub_distrib]
      refine Finset.sum_congr rfl fun d _ => ?_
      ring
    rw [e2]
    refine le_trans (Finset.abs_sum_le_sum_abs _ _) (Finset.sum_le_sum fun d _ => ?_)
    have hs : |(Opn.E69.sign M d : ℝ)| = 1 := by
      unfold Opn.E69.sign; push_cast; rw [Finset.abs_prod]; simp
    rw [abs_mul, hs, one_mul]
  have hmean : ‖Opn.E69.charMean q M P n₀ T - 1‖
      ≤ 2 * Real.pi * ∑ d : Fin M → Fin 6, (∑ t ∈ Finset.range T, δ d t) / T := by
    unfold Opn.E69.charMean
    have hTC : (T : ℂ) ≠ 0 := by exact_mod_cast hT.ne'
    have e : ∀ S : ℂ, S / (T : ℂ) - 1 = (S - ∑ _t ∈ Finset.range T, (1 : ℂ)) / T := by
      intro S; simp; field_simp
    rw [e, ← Finset.sum_sub_distrib, norm_div, Complex.norm_natCast]
    calc _ ≤ (∑ t ∈ Finset.range T, 2 * Real.pi * ∑ d : Fin M → Fin 6, δ d t) / T := by
          refine div_le_div_of_nonneg_right ?_ hTR.le
          exact le_trans (norm_sum_le _ _) (Finset.sum_le_sum fun t _ => hpt t)
      _ = _ := by
          rw [← Finset.mul_sum, Finset.sum_comm, mul_div_assoc, Finset.sum_div]
  have hsum : ∑ d : Fin M → Fin 6, (∑ t ∈ Finset.range T, δ d t) / T < (q : ℝ) * (2 * ε) := by
    refine lt_of_le_of_lt (Finset.sum_le_sum fun d _ => hline d) ?_
    rw [← Finset.mul_sum, Finset.sum_add_distrib, Finset.sum_const, ← Finset.sum_div]
    have hc : (Finset.univ : Finset (Fin M → Fin 6)).card = 6 ^ M := by simp
    rw [hc, nsmul_eq_mul]
    push_cast
    have : (q : ℝ) * ((6 : ℝ) ^ M * (5 / Real.log P)
        + (∑ d : Fin M → Fin 6, ((Opn.E69.dil M P d).primeFactors.card : ℝ)) / T)
        < (q : ℝ) * (2 * ε) := by
      apply mul_lt_mul_of_pos_left _ hqR
      linarith
    exact this
  have h1 : (1 : ℝ) ≤ ‖Opn.E69.charMean q M P n₀ T‖ + ‖Opn.E69.charMean q M P n₀ T - 1‖ := by
    have := norm_sub_le (Opn.E69.charMean q M P n₀ T) (Opn.E69.charMean q M P n₀ T - 1)
    simpa using this
  have hπ : Real.pi < 13 / 4 := by linarith [Real.pi_lt_d2]
  have hε1 : ε * (2 + 26 * (q : ℝ)) = 1 := by rw [hε]; field_simp
  have hb : 2 * Real.pi * ((q : ℝ) * (2 * ε)) ≤ 13 * (q : ℝ) * ε := by
    have : 0 ≤ (q : ℝ) * ε := by positivity
    nlinarith [Real.pi_pos]
  have : 2 * Real.pi * ∑ d : Fin M → Fin 6, (∑ t ∈ Finset.range T, δ d t) / T
      ≤ 2 * Real.pi * ((q : ℝ) * (2 * ε)) :=
    mul_le_mul_of_nonneg_left hsum.le (by positivity)
  nlinarith
