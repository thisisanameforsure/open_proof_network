import Mathlib

open scoped ArithmeticFunction.omega

theorem erdos_69_existential_decay_circular :
    (Irrational <| ∑' n, ω (n + 2) / 2 ^ (n + 2)) →
    ∀ q : ℕ, 0 < q → ∀ ε : ℝ, 0 < ε →
      ∃ (n T : ℕ) (a b Q : Fin n → ℕ) (c : Fin n → ℤ), 0 < T ∧ (∀ i, a i ≠ 0) ∧
        (∀ i, ∀ p ∈ (a i).primeFactors, Nat.Coprime p (Q i)) ∧
        (∑ t ∈ Finset.range T, ∑ i, |(c i : ℝ)| *
            ∑ p ∈ (a i).primeFactors, (2 : ℝ) ^ ((b i + Q i * t) % p) / (2 ^ p - 1)) / T < ε ∧
        ‖∑ t ∈ Finset.range T, Complex.exp (2 * Real.pi * Complex.I *
            (((q : ℝ) * ∑ i, (c i : ℝ) *
              ∑' k : ℕ, (ω (a i * (b i + Q i * t + (k + 1))) : ℝ) / 2 ^ (k + 1) : ℝ) : ℂ))‖ / T
          < ε := by
  intro hroot q hq ε hε
  set R : ℝ := ∑' n : ℕ, (ω (n + 2) : ℝ) / 2 ^ (n + 2) with hR
  have hirr : Irrational ((q : ℝ) * R) := hroot.natCast_mul hq.ne'
  have hsum : Summable (fun n : ℕ => (ω (n + 2) : ℝ) / 2 ^ (n + 2)) := by
    by_contra h
    have h0 : R = 0 := tsum_eq_zero_of_not_summable h
    rw [h0] at hroot
    exact hroot.ne_zero rfl
  have hT0 : ∑' k : ℕ, (ω (1 * (0 + 1 * 0 + (k + 1))) : ℝ) / 2 ^ (k + 1) = R := by
    have hs1 : Summable (fun k : ℕ => (ω (k + 1) : ℝ) / 2 ^ (k + 1)) :=
      (summable_nat_add_iff (f := fun k : ℕ => (ω (k + 1) : ℝ) / 2 ^ (k + 1)) 1).1 hsum
    simp only [one_mul, mul_zero, zero_add, add_zero]
    rw [hs1.tsum_eq_zero_add]
    simp [hR]
  have hT1 : ∑' k : ℕ, (ω (1 * (0 + 1 * 1 + (k + 1))) : ℝ) / 2 ^ (k + 1) = 2 * R := by
    simp only [one_mul, mul_one, zero_add]
    rw [hR, ← tsum_mul_left]
    refine tsum_congr fun k => ?_
    rw [show 1 + (k + 1) = k + 2 by omega]
    field_simp
    ring
  have hd : Dense ((AddSubgroup.closure {(q : ℝ) * R, 1} : AddSubgroup ℝ) : Set ℝ) := by
    rw [dense_addSubgroupClosure_pair_iff]
    simpa using hirr
  obtain ⟨y, hy, hyd⟩ := hd.exists_dist_lt (1 / 2 : ℝ) (show (0 : ℝ) < ε / 4 by positivity)
  obtain ⟨m, n', rfl⟩ := AddSubgroup.mem_closure_pair.1 hy
  refine ⟨1, 2, fun _ => 1, fun _ => 0, fun _ => 1, fun _ => m, by norm_num, by simp, by simp,
    by simpa using hε, ?_⟩
  simp only [Finset.sum_range_succ, Finset.range_zero, Finset.sum_empty, Finset.univ_unique,
    Finset.sum_singleton, zero_add]
  rw [hT0, hT1]
  have hw : |(m : ℝ) * ((q : ℝ) * R) + n' - 1 / 2| < ε / 4 := by
    have h := hyd
    rw [Real.dist_eq, abs_sub_comm] at h
    simpa [zsmul_eq_mul] using h
  set v : ℝ := 2 * Real.pi * ((m : ℝ) * ((q : ℝ) * R) + n' - 1 / 2) with hv
  set X : ℂ := Complex.exp (Complex.I * (v : ℂ)) with hX
  have hE : Complex.exp (2 * ↑Real.pi * Complex.I * ((↑q * (↑m * R) : ℝ) : ℂ)) = -X := by
    have h1 : Complex.I * (v : ℂ) = 2 * ↑Real.pi * Complex.I * ((↑q * (↑m * R) : ℝ) : ℂ)
        + (n' : ℂ) * (2 * ↑Real.pi * Complex.I) + -(↑Real.pi * Complex.I) := by
      rw [hv]; push_cast; ring
    rw [hX, h1, Complex.exp_add, Complex.exp_add, Complex.exp_int_mul_two_pi_mul_I,
      Complex.exp_neg, Complex.exp_pi_mul_I]
    norm_num
  have hE2 : Complex.exp (2 * ↑Real.pi * Complex.I * ((↑q * (↑m * (2 * R)) : ℝ) : ℂ)) = X * X := by
    have h2 : 2 * ↑Real.pi * Complex.I * ((↑q * (↑m * (2 * R)) : ℝ) : ℂ)
        = 2 * ↑Real.pi * Complex.I * ((↑q * (↑m * R) : ℝ) : ℂ)
          + 2 * ↑Real.pi * Complex.I * ((↑q * (↑m * R) : ℝ) : ℂ) := by
      push_cast; ring
    rw [h2, Complex.exp_add, hE]; ring
  rw [hE, hE2, show -X + X * X = X * (X - 1) by ring, norm_mul]
  have hX1 : ‖X‖ = 1 := by
    rw [hX, mul_comm]; exact Complex.norm_exp_ofReal_mul_I v
  have hX2 : ‖X - 1‖ ≤ ‖v‖ := by
    rw [hX]; exact Real.norm_exp_I_mul_ofReal_sub_one_le
  have hv' : ‖v‖ < 2 * ε := by
    rw [Real.norm_eq_abs, hv, abs_mul, abs_of_pos (by positivity : (0 : ℝ) < 2 * Real.pi)]
    nlinarith [Real.pi_lt_four, Real.pi_pos, abs_nonneg ((m : ℝ) * ((q : ℝ) * R) + n' - 1 / 2)]
  rw [hX1, one_mul]
  have : ‖X - 1‖ < 2 * ε := lt_of_le_of_lt hX2 hv'
  rw [div_lt_iff₀ (by norm_num)]
  push_cast
  linarith
