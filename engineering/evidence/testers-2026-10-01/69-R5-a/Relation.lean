import Mathlib

open scoped ArithmeticFunction.omega

/-! 69-R5-a: 69-R4-b's BridgeRoot.lean recast as the relation proof of a `resolves` variant
(`theorem relation : <variant's type> → <root's type>`), so that the bridge can be a PROPOSED node whose
header imports `Defs.Construction` and whose deps include spec-84446025. Original comment: Root of erdos-69 from ONE hole stated over Mathlib only (69-R4-b, 2026-10-01).
The root's `Statement.lean` imports Mathlib alone and a proof may not add an import, so no hole
of a root skeleton can mention `Opn.E69.*`. The hole below (`bridge`) says the same thing as the
construction + decay holes of 69-R2-b's skeleton without naming the definitions. The proved
node `spec-84446025` is restated as a node Context does. -/

-- proved node spec-84446025 (declared dependency)
theorem Opn.erdos_69_rational_dilated_tails_near_integers :
    ∀ (q : ℕ) (z : ℤ), (q : ℝ) * ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = z →
      ∀ (a Q b T : ℕ), a ≠ 0 → 0 < T → (∀ p ∈ a.primeFactors, Nat.Coprime p Q) →
        (∑ t ∈ Finset.range T,
            |(q : ℝ) * ∑' k : ℕ, (ω (a * (b + Q * t + (k + 1))) : ℝ) / 2 ^ (k + 1)
              - round ((q : ℝ) * ∑' k : ℕ, (ω (a * (b + Q * t + (k + 1))) : ℝ) / 2 ^ (k + 1))|) / T
          ≤ (q : ℝ) * ∑ p ∈ a.primeFactors, ((1 : ℝ) / p + 1 / T) := by
  sorry

theorem relation :
    (∀ (q : ℕ), 0 < q → ∀ ε : ℝ, 0 < ε →
      ∃ (M T : ℕ) (a b Q : (Fin M → Fin 6) → ℕ) (s : (Fin M → Fin 6) → ℤ), 0 < T ∧
        (∀ i, a i ≠ 0) ∧ (∀ i, s i = 1 ∨ s i = -1) ∧
        (∀ i, ∀ p ∈ (a i).primeFactors, Nat.Coprime p (Q i)) ∧
        ∑ i : Fin M → Fin 6, ∑ p ∈ (a i).primeFactors, ((1 : ℝ) / p + 1 / T) < ε ∧
        ‖(∑ t ∈ Finset.range T, Complex.exp (2 * Real.pi * Complex.I *
            (((q : ℝ) * ∑ i : Fin M → Fin 6, (s i : ℝ) *
              ∑' k : ℕ, (ω (a i * (b i + Q i * t + (k + 1))) : ℝ) / 2 ^ (k + 1) : ℝ) : ℂ))) / T‖
          < ε) →
    (Irrational <| ∑' n, ω (n + 2) / 2 ^ (n + 2)) := by
  intro bridge
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
  set ε : ℝ := 1 / (1 + 7 * (q : ℝ)) with hε
  have hεpos : 0 < ε := by positivity
  obtain ⟨M, T, a, b, Q, s, hT, ha, hs, hcop, hbud, hdecay⟩ := bridge q hqpos ε hεpos
  have hTR : (0 : ℝ) < T := by exact_mod_cast hT
  set τ : (Fin M → Fin 6) → ℕ → ℝ := fun i t =>
    (q : ℝ) * ∑' k : ℕ, (ω (a i * (b i + Q i * t + (k + 1))) : ℝ) / 2 ^ (k + 1) with hτ
  set δ : (Fin M → Fin 6) → ℕ → ℝ := fun i t => |τ i t - round (τ i t)| with hδ
  have hline : ∀ i : Fin M → Fin 6, (∑ t ∈ Finset.range T, δ i t) / T
      ≤ (q : ℝ) * ∑ p ∈ (a i).primeFactors, ((1 : ℝ) / p + 1 / T) := fun i =>
    Opn.erdos_69_rational_dilated_tails_near_integers q r.num hqz (a i) (Q i) (b i) T
      (ha i) hT (hcop i)
  set S : ℕ → ℝ := fun t => (q : ℝ) * ∑ i : Fin M → Fin 6, (s i : ℝ) *
    ∑' k : ℕ, (ω (a i * (b i + Q i * t + (k + 1))) : ℝ) / 2 ^ (k + 1) with hS
  have hpt : ∀ t : ℕ, ‖Complex.exp (2 * Real.pi * Complex.I * ((S t : ℝ) : ℂ)) - 1‖
      ≤ 2 * Real.pi * ∑ i : Fin M → Fin 6, δ i t := by
    intro t
    have hθ : S t = ∑ i : Fin M → Fin 6, (s i : ℝ) * τ i t := by
      rw [hS, hτ]
      simp only
      rw [Finset.mul_sum]
      refine Finset.sum_congr rfl fun i _ => ?_
      ring
    set k : ℤ := ∑ i : Fin M → Fin 6, s i * round (τ i t) with hk
    set v : ℝ := 2 * Real.pi * (∑ i : Fin M → Fin 6, (s i : ℝ) * τ i t - k) with hv
    have hexp : Complex.exp (2 * Real.pi * Complex.I * ((S t : ℝ) : ℂ))
        = Complex.exp (Complex.I * (v : ℂ)) := by
      rw [hθ]
      have e : 2 * (Real.pi : ℂ) * Complex.I *
          ((∑ i : Fin M → Fin 6, (s i : ℝ) * τ i t : ℝ) : ℂ)
          = Complex.I * (v : ℂ) + (k : ℂ) * (2 * Real.pi * Complex.I) := by
        rw [hv]; push_cast; ring
      rw [e, Complex.exp_add, Complex.exp_int_mul_two_pi_mul_I, mul_one]
    rw [hexp]
    refine le_trans Real.norm_exp_I_mul_ofReal_sub_one_le ?_
    rw [Real.norm_eq_abs, hv, abs_mul, abs_of_pos Real.two_pi_pos]
    refine mul_le_mul_of_nonneg_left ?_ Real.two_pi_pos.le
    have e2 : ∑ i : Fin M → Fin 6, (s i : ℝ) * τ i t - (k : ℝ)
        = ∑ i : Fin M → Fin 6, (s i : ℝ) * (τ i t - round (τ i t)) := by
      rw [hk]; push_cast; rw [← Finset.sum_sub_distrib]
      refine Finset.sum_congr rfl fun i _ => ?_
      ring
    rw [e2]
    refine le_trans (Finset.abs_sum_le_sum_abs _ _) (Finset.sum_le_sum fun i _ => ?_)
    have hs1 : |(s i : ℝ)| = 1 := by
      rcases hs i with h | h <;> rw [h] <;> simp
    rw [abs_mul, hs1, one_mul]
  set cm : ℂ := (∑ t ∈ Finset.range T, Complex.exp (2 * Real.pi * Complex.I *
    ((S t : ℝ) : ℂ))) / T with hcm
  have hmean : ‖cm - 1‖
      ≤ 2 * Real.pi * ∑ i : Fin M → Fin 6, (∑ t ∈ Finset.range T, δ i t) / T := by
    rw [hcm]
    have hTC : (T : ℂ) ≠ 0 := by exact_mod_cast hT.ne'
    have e : ∀ W : ℂ, W / (T : ℂ) - 1 = (W - ∑ _t ∈ Finset.range T, (1 : ℂ)) / T := by
      intro W; simp; field_simp
    rw [e, ← Finset.sum_sub_distrib, norm_div, Complex.norm_natCast]
    calc _ ≤ (∑ t ∈ Finset.range T, 2 * Real.pi * ∑ i : Fin M → Fin 6, δ i t) / T := by
          refine div_le_div_of_nonneg_right ?_ hTR.le
          exact le_trans (norm_sum_le _ _) (Finset.sum_le_sum fun t _ => hpt t)
      _ = _ := by
          rw [← Finset.mul_sum, Finset.sum_comm, mul_div_assoc, Finset.sum_div]
  have hsum : ∑ i : Fin M → Fin 6, (∑ t ∈ Finset.range T, δ i t) / T ≤ (q : ℝ) * ε := by
    refine le_trans (Finset.sum_le_sum fun i _ => hline i) ?_
    rw [← Finset.mul_sum]
    exact mul_le_mul_of_nonneg_left hbud.le hqR.le
  have hdec : ‖cm‖ < ε := hdecay
  have h1 : (1 : ℝ) ≤ ‖cm‖ + ‖cm - 1‖ := by
    have := norm_sub_le cm (cm - 1)
    simpa using this
  have hε1 : ε * (1 + 7 * (q : ℝ)) = 1 := by rw [hε]; field_simp
  have hπ : 2 * Real.pi ≤ 7 := by linarith [Real.pi_lt_d2]
  have hqε : 0 ≤ (q : ℝ) * ε := by positivity
  have : 2 * Real.pi * ∑ i : Fin M → Fin 6, (∑ t ∈ Finset.range T, δ i t) / T
      ≤ 7 * ((q : ℝ) * ε) := by
    calc _ ≤ 2 * Real.pi * ((q : ℝ) * ε) := mul_le_mul_of_nonneg_left hsum (by positivity)
      _ ≤ _ := mul_le_mul_of_nonneg_right hπ hqε
  nlinarith
