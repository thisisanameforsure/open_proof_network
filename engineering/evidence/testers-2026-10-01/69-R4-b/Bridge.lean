import Mathlib
import Defs.Construction

open scoped ArithmeticFunction.omega

/-! The bridge (69-R4-b, 2026-10-01): a statement over Mathlib only, proposed as a node whose
header imports `Defs.Construction`, so that its holes may use the definitions. Skeleton: the
bridge from holes h1..h4 of 69-R2-b's skeleton and the proved node `spec-e0b917d1`. -/

-- proved node spec-e0b917d1 (declared dependency)
theorem Opn.erdos_69_rough_dilation_reciprocal :
    ∀ P j : ℕ, 2 ≤ P → j ≤ P →
      ∑ p ∈ (1 + primorial P * (1 + j)).primeFactors, (1 : ℝ) / p ≤ 5 / Real.log P := by
  sorry

theorem Opn.erdos_69_signed_family_bridge : ∀ (q : ℕ), 0 < q → ∀ ε : ℝ, 0 < ε →
    ∃ (M T : ℕ) (a b Q : (Fin M → Fin 6) → ℕ) (s : (Fin M → Fin 6) → ℤ), 0 < T ∧
      (∀ i, a i ≠ 0) ∧ (∀ i, s i = 1 ∨ s i = -1) ∧
      (∀ i, ∀ p ∈ (a i).primeFactors, Nat.Coprime p (Q i)) ∧
      ∑ i : Fin M → Fin 6, ∑ p ∈ (a i).primeFactors, ((1 : ℝ) / p + 1 / T) < ε ∧
      ‖(∑ t ∈ Finset.range T, Complex.exp (2 * Real.pi * Complex.I *
          (((q : ℝ) * ∑ i : Fin M → Fin 6, (s i : ℝ) *
            ∑' k : ℕ, (ω (a i * (b i + Q i * t + (k + 1))) : ℝ) / 2 ^ (k + 1) : ℝ) : ℂ))) / T‖
        < ε := by
  -- h1 (digits; PROVED, H1.lean)
  have h1 : ∀ (M : ℕ) (d : Fin M → Fin 6), Opn.E69.gIndex M d < 7 ^ M := by
    sorry
  -- h2 (coprimality; PROVED, H2.lean)
  have h2 : ∀ (M P : ℕ), 7 ^ M ≤ P → ∀ (d : Fin M → Fin 6),
      ∀ p ∈ (Opn.E69.dil M P d).primeFactors, Nat.Coprime p (Opn.E69.step M P d) := by
    sorry
  -- h3 (the construction exists; PROVED, H3.lean)
  have h3 : ∀ (M P : ℕ), 7 ^ M ≤ P →
      ∃ n₀ : ℕ, n₀ < Opn.E69.modulus M P ∧ Opn.E69.Admissible M P n₀ := by
    sorry
  -- h4 (decay; the theorem; second layer in H4Skeleton.lean)
  have h4 : ∀ (q : ℕ), 0 < q → ∀ ε : ℝ, 0 < ε →
      ∃ M P T : ℕ, 2 ≤ P ∧ 7 ^ M ≤ P ∧ 0 < T ∧
        (6 : ℝ) ^ M * (5 / Real.log P) < ε ∧
        (∑ d : Fin M → Fin 6, ((Opn.E69.dil M P d).primeFactors.card : ℝ)) / T < ε ∧
        ∀ n₀ : ℕ, n₀ < Opn.E69.modulus M P → Opn.E69.Admissible M P n₀ →
          ‖Opn.E69.charMean q M P n₀ T‖ < ε := by
    sorry
  intro q hq ε hε
  obtain ⟨M, P, T, hP2, hP7, hT, hlog, hcard, hdec⟩ := h4 q hq (ε / 2) (by positivity)
  obtain ⟨n₀, hn₀, hadm⟩ := h3 M P hP7
  refine ⟨M, T, Opn.E69.dil M P, Opn.E69.start M P n₀, Opn.E69.step M P, Opn.E69.sign M, hT,
    fun i => by unfold Opn.E69.dil; omega, fun i => ?_, h2 M P hP7, ?_, ?_⟩
  · unfold Opn.E69.sign
    refine Finset.prod_induction _ (fun x : ℤ => x = 1 ∨ x = -1) ?_ (Or.inl rfl)
      (fun r _ => neg_one_pow_eq_or ℤ _)
    rintro x y (rfl | rfl) (rfl | rfl) <;> simp
  · have hrec : ∀ d : Fin M → Fin 6,
        ∑ p ∈ (Opn.E69.dil M P d).primeFactors, (1 : ℝ) / p ≤ 5 / Real.log P := fun d =>
      Opn.erdos_69_rough_dilation_reciprocal P (Opn.E69.gIndex M d) hP2
        (le_trans (h1 M d).le hP7)
    have hsplit : ∀ d : Fin M → Fin 6,
        ∑ p ∈ (Opn.E69.dil M P d).primeFactors, ((1 : ℝ) / p + 1 / T)
          ≤ 5 / Real.log P + ((Opn.E69.dil M P d).primeFactors.card : ℝ) / T := by
      intro d
      rw [Finset.sum_add_distrib, Finset.sum_const, nsmul_eq_mul]
      have e : ((Opn.E69.dil M P d).primeFactors.card : ℝ) * (1 / (T : ℝ))
          = ((Opn.E69.dil M P d).primeFactors.card : ℝ) / T := by ring
      have := hrec d
      linarith
    refine lt_of_le_of_lt (Finset.sum_le_sum fun d _ => hsplit d) ?_
    rw [Finset.sum_add_distrib, Finset.sum_const, ← Finset.sum_div]
    have hc : (Finset.univ : Finset (Fin M → Fin 6)).card = 6 ^ M := by simp
    rw [hc, nsmul_eq_mul]
    push_cast
    linarith
  · have h := hdec n₀ hn₀ hadm
    unfold Opn.E69.charMean Opn.E69.signedTail Opn.E69.tail at h
    exact lt_trans h (by linarith)
