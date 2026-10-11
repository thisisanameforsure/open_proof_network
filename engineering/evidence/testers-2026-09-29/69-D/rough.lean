import Mathlib

theorem rough_dilation_reciprocal :
    ∀ P j : ℕ, 2 ≤ P → j ≤ P →
      ∑ p ∈ (1 + primorial P * (1 + j)).primeFactors, (1 : ℝ) / p ≤ 5 / Real.log P := by
  intro P j hP hj
  set a := 1 + primorial P * (1 + j) with ha_def
  set s := a.primeFactors with hs_def
  have ha0 : a ≠ 0 := by omega
  -- every prime factor of a exceeds P
  have hbig : ∀ p ∈ s, P < p := by
    intro p hp
    have hpp : p.Prime := Nat.prime_of_mem_primeFactors hp
    have hpa : p ∣ a := Nat.dvd_of_mem_primeFactors hp
    by_contra hle
    push Not at hle
    have hprim : p ∣ primorial P := by
      unfold primorial
      exact Finset.dvd_prod_of_mem (fun q => q)
        (Finset.mem_filter.mpr ⟨Finset.mem_range.mpr (by omega), hpp⟩)
    have h1 : p ∣ primorial P * (1 + j) := Dvd.dvd.mul_right hprim _
    have : p ∣ 1 := (Nat.dvd_add_right h1).mp (by rw [add_comm]; exact hpa)
    exact hpp.one_lt.ne' (Nat.dvd_one.mp this)
  -- the sum is at most card / P
  have hPpos : (0 : ℝ) < P := by exact_mod_cast (show 0 < P by omega)
  have hsum : ∑ p ∈ s, (1 : ℝ) / p ≤ s.card * (1 / (P : ℝ)) := by
    have : ∀ p ∈ s, (1 : ℝ) / p ≤ 1 / (P : ℝ) := by
      intro p hp
      have : (P : ℝ) ≤ p := by exact_mod_cast (hbig p hp).le
      exact one_div_le_one_div_of_le hPpos this
    calc ∑ p ∈ s, (1 : ℝ) / p ≤ ∑ _p ∈ s, 1 / (P : ℝ) := Finset.sum_le_sum this
      _ = s.card * (1 / (P : ℝ)) := by rw [Finset.sum_const, nsmul_eq_mul]
  -- P ^ card ≤ a ≤ 16 ^ P
  have hcard : P ^ s.card ≤ a := by
    calc P ^ s.card ≤ ∏ p ∈ s, p := Finset.pow_card_le_prod s (fun p => p) P (fun p hp => (hbig p hp).le)
      _ ≤ a := Nat.le_of_dvd (by omega) (Nat.prod_primeFactors_dvd a)
  have aux : ∀ n : ℕ, n + 2 ≤ 2 * 4 ^ n := by
    intro n
    induction n with
    | zero => norm_num
    | succ n ih => rw [pow_succ]; omega
  have ha16 : a ≤ 2 * 16 ^ P := by
    have h4 := primorial_le_four_pow P
    have hP4 := aux P
    calc a = 1 + primorial P * (1 + j) := rfl
      _ ≤ 1 + 4 ^ P * (1 + P) := by gcongr
      _ ≤ 4 ^ P * (2 + P) := by nlinarith [Nat.one_le_pow P 4 (by norm_num)]
      _ ≤ 4 ^ P * (2 * 4 ^ P) := Nat.mul_le_mul_left _ (by omega)
      _ = 2 * 16 ^ P := by rw [show (16 : ℕ) = 4 * 4 by norm_num, mul_pow]; ring
  -- logs
  have hlogP : 0 < Real.log P := Real.log_pos (by exact_mod_cast (show 1 < P by omega))
  have hkey : (s.card : ℝ) * Real.log P ≤ 5 * P := by
    have h1 : ((P : ℝ)) ^ s.card ≤ 2 * (16 : ℝ) ^ P := by
      exact_mod_cast hcard.trans ha16
    have h2 := Real.log_le_log (by positivity) h1
    rw [Real.log_mul (by norm_num) (by positivity), Real.log_pow, Real.log_pow] at h2
    have h16 : Real.log 16 = 4 * Real.log 2 := by
      rw [show (16 : ℝ) = 2 ^ 4 by norm_num, Real.log_pow]; norm_num
    have hl2 := Real.log_two_lt_d9
    have hl2' : 0 < Real.log 2 := Real.log_pos (by norm_num)
    have hP1 : (1 : ℝ) ≤ P := by exact_mod_cast (show 1 ≤ P by omega)
    rw [h16] at h2
    nlinarith
  calc ∑ p ∈ s, (1 : ℝ) / p ≤ s.card * (1 / (P : ℝ)) := hsum
    _ ≤ 5 / Real.log P := by
      rw [mul_one_div, div_le_div_iff₀ hPpos hlogP]
      linarith
