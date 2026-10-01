import Mathlib
import Nodes.«spec-e0b917d1».Context

/-! A speculative ingredient for erdos-69 (D-29): the correction mass of a rough dilation.
In the composite-dilation route to the irrationality of `∑ ω(n)/2^n` (see the annex on
`erdos-69` describing github.com/plby/lean-proofs, `ErdosProblems/Erdos69/RoughSizeBounds.lean`,
`roughDilation_reciprocal_mass_le`), dilating the sequence by `a = 1 + P# · (1 + j)` changes
the binary tail by a correction whose mean is controlled by `∑_{p ∣ a} 1/p`. Every prime factor of
`a` exceeds `P`, and `a ≤ 16^P`, so that sum is at most `5 / log P`. -/

theorem Opn.erdos_69_rough_dilation_reciprocal :
    ∀ P j : ℕ, 2 ≤ P → j ≤ P →
      ∑ p ∈ (1 + primorial P * (1 + j)).primeFactors, (1 : ℝ) / p ≤ 5 / Real.log P := by
  intro P j hP hj
  set a : ℕ := 1 + primorial P * (1 + j) with ha
  have ha0 : a ≠ 0 := by omega
  -- every prime factor of a exceeds P
  have hbig : ∀ p ∈ a.primeFactors, P < p := by
    intro p hp
    have hpp : p.Prime := Nat.prime_of_mem_primeFactors hp
    have hpd : p ∣ a := Nat.dvd_of_mem_primeFactors hp
    by_contra hle
    push Not at hle
    have hprim : p ∣ primorial P := by
      apply Finset.dvd_prod_of_mem
      rw [Finset.mem_filter, Finset.mem_range]
      exact ⟨by omega, hpp⟩
    have hpd' : p ∣ primorial P * (1 + j) + 1 := by rw [add_comm]; exact hpd
    have h1 : p ∣ 1 := (Nat.dvd_add_right (dvd_mul_of_dvd_left hprim (1 + j))).mp hpd'
    exact hpp.one_lt.ne' (Nat.dvd_one.mp h1)
  set k := a.primeFactors.card with hk
  have hPpos : (0 : ℝ) < P := by exact_mod_cast (show 0 < P by omega)
  have hlogP : 0 < Real.log P := Real.log_pos (by exact_mod_cast (show 1 < P by omega))
  -- P^k ≤ a
  have hpow : (P : ℝ) ^ k ≤ a := by
    have h1 : P ^ k ≤ ∏ p ∈ a.primeFactors, p := by
      rw [hk]
      exact Finset.pow_card_le_prod _ _ _ (fun p hp => (hbig p hp).le)
    have h2 : ∏ p ∈ a.primeFactors, p ≤ a :=
      Nat.le_of_dvd (Nat.pos_of_ne_zero ha0) (Nat.prod_primeFactors_dvd a)
    exact_mod_cast h1.trans h2
  -- a ≤ 16^P
  have ha16 : a ≤ 16 ^ P := by
    have h4 : primorial P ≤ 4 ^ P := primorial_le_four_pow P
    have h2 : P + 2 ≤ 4 ^ P := by
      have : P < 2 ^ P := Nat.lt_two_pow_self
      have : 4 ^ P = 2 ^ P * 2 ^ P := by rw [← mul_pow]; norm_num
      nlinarith [Nat.one_le_two_pow (n := P)]
    have h16 : 16 ^ P = 4 ^ P * 4 ^ P := by rw [← mul_pow]; norm_num
    have : primorial P * (1 + j) ≤ 4 ^ P * (1 + P) := Nat.mul_le_mul h4 (by omega)
    nlinarith
  -- log a ≤ 5 P
  have hloga : Real.log a ≤ 5 * P := by
    have hapos : (0 : ℝ) < a := by exact_mod_cast Nat.pos_of_ne_zero ha0
    have h16 : (a : ℝ) ≤ 16 ^ P := by exact_mod_cast ha16
    have he : (16 : ℝ) ≤ Real.exp 5 := by
      have h2 : (2 : ℝ) ≤ Real.exp 1 := by
        have := Real.add_one_le_exp (1 : ℝ); linarith
      have : Real.exp 5 = Real.exp 1 ^ 5 := by rw [← Real.exp_nat_mul]; norm_num
      rw [this]
      nlinarith [pow_le_pow_left₀ (by norm_num) h2 5]
    calc Real.log a ≤ Real.log (16 ^ P) := Real.log_le_log hapos h16
      _ = P * Real.log 16 := by rw [Real.log_pow]
      _ ≤ P * 5 := by
          apply mul_le_mul_of_nonneg_left _ hPpos.le
          rw [Real.log_le_iff_le_exp (by norm_num)]; exact he
      _ = 5 * P := by ring
  -- k log P ≤ log a
  have hklog : (k : ℝ) * Real.log P ≤ Real.log a := by
    have := Real.log_le_log (by positivity) hpow
    rwa [Real.log_pow] at this
  -- the sum is at most k / P
  have hsum : ∑ p ∈ a.primeFactors, (1 : ℝ) / p ≤ k * (1 / P) := by
    have := Finset.sum_le_card_nsmul a.primeFactors (fun p : ℕ => (1 : ℝ) / p) (1 / P)
      (fun p hp => by
        have hp' : (P : ℝ) ≤ p := by exact_mod_cast (hbig p hp).le
        exact one_div_le_one_div_of_le hPpos hp')
    simpa [hk, nsmul_eq_mul] using this
  calc ∑ p ∈ a.primeFactors, (1 : ℝ) / p ≤ k * (1 / P) := hsum
    _ ≤ 5 / Real.log P := by
      rw [le_div_iff₀ hlogP]
      have : (k : ℝ) * Real.log P ≤ 5 * P := hklog.trans hloga
      calc (k : ℝ) * (1 / P) * Real.log P = (k * Real.log P) / P := by ring
        _ ≤ (5 * P) / P := by gcongr
        _ = 5 := by field_simp
