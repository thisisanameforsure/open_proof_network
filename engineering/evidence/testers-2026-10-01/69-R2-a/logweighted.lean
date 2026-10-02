import Mathlib
theorem T1 : ∃ C : ℝ, ∀ n : ℕ, |∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ) - Real.log n| ≤ C := by
  -- (a) Stirling lower bound, by induction
  have hstir : ∀ n : ℕ, (n : ℝ) * Real.log n - n ≤ Real.log (n.factorial : ℝ) := by
    intro n
    induction n with
    | zero => simp
    | succ n ih =>
      have hf : (0 : ℝ) < (n.factorial : ℝ) := by exact_mod_cast n.factorial_pos
      have hn1 : (0 : ℝ) < ((n + 1 : ℕ) : ℝ) := by positivity
      rw [Nat.factorial_succ, Nat.cast_mul, Real.log_mul hn1.ne' hf.ne']
      rcases Nat.eq_zero_or_pos n with h0 | hpos
      · subst h0
        simp
      · have hn0 : (0 : ℝ) < n := by exact_mod_cast hpos
        have h1 : Real.log ((n + 1 : ℕ) : ℝ) - Real.log (n : ℝ)
            = Real.log (((n + 1 : ℕ) : ℝ) / n) := (Real.log_div hn1.ne' hn0.ne').symm
        have h2 := Real.log_le_sub_one_of_pos (show 0 < ((n + 1 : ℕ) : ℝ) / n by positivity)
        have h3 : (n : ℝ) * (((n + 1 : ℕ) : ℝ) / n - 1) = 1 := by
          push_cast
          field_simp
          ring
        have h4 : (n : ℝ) * (Real.log ((n + 1 : ℕ) : ℝ) - Real.log (n : ℝ)) ≤ 1 := by
          rw [h1, ← h3]
          exact mul_le_mul_of_nonneg_left h2 hn0.le
        push_cast at h4 ih ⊢
        nlinarith
  -- (b) the prime-power tail: ∑_{2 ≤ m ≤ k+1} log m / (m (m-1)) ≤ 2
  have htail : ∀ k : ℕ, ∑ m ∈ Finset.Icc 2 (k + 1), Real.log (m : ℝ) / ((m : ℝ) * ((m : ℝ) - 1))
      ≤ 2 - (Real.log ((k + 1 : ℕ) : ℝ) + 2) / ((k + 1 : ℕ) : ℝ) := by
    intro k
    induction k with
    | zero => simp
    | succ k ih =>
      rw [Finset.sum_Icc_succ_top (by omega)]
      have ha : (0 : ℝ) < ((k + 1 : ℕ) : ℝ) := by positivity
      have ha1 : (1 : ℝ) ≤ ((k + 1 : ℕ) : ℝ) := by exact_mod_cast (by omega : 1 ≤ k + 1)
      have hb : (0 : ℝ) < ((k + 1 + 1 : ℕ) : ℝ) := by positivity
      have hbe : ((k + 1 + 1 : ℕ) : ℝ) = ((k + 1 : ℕ) : ℝ) + 1 := by push_cast; ring
      have h1 : Real.log ((k + 1 + 1 : ℕ) : ℝ) - Real.log ((k + 1 : ℕ) : ℝ)
          = Real.log (((k + 1 + 1 : ℕ) : ℝ) / ((k + 1 : ℕ) : ℝ)) :=
        (Real.log_div hb.ne' ha.ne').symm
      have h2 := Real.log_le_sub_one_of_pos
        (show 0 < ((k + 1 + 1 : ℕ) : ℝ) / ((k + 1 : ℕ) : ℝ) by positivity)
      rw [← h1, hbe] at h2
      rw [hbe] at hb ⊢
      generalize ((k + 1 : ℕ) : ℝ) = a at *
      generalize Real.log a = L1 at *
      generalize Real.log (a + 1) = L2 at *
      have h3 : (a + 1) / a - 1 = 1 / a := by field_simp; ring
      have h4 : a * (L2 - L1) ≤ 1 := by
        have := mul_le_mul_of_nonneg_left h2 ha.le
        rw [h3] at this
        have e : a * (1 / a) = 1 := by field_simp
        linarith
      have h5 : L2 - L1 ≤ 1 := by
        have : 1 / a ≤ 1 := by rw [div_le_one ha]; exact ha1
        linarith [h3 ▸ h2]
      have e : (L1 + 2) / a - (L2 + 2) / (a + 1) - L2 / ((a + 1) * (a + 1 - 1))
          = (2 - (a * (L2 - L1) + (L2 - L1))) / (a * (a + 1)) := by
        rw [show a + 1 - 1 = a by ring]
        field_simp
        ring
      have : 0 ≤ (2 - (a * (L2 - L1) + (L2 - L1))) / (a * (a + 1)) :=
        div_nonneg (by linarith) (by positivity)
      linarith
  refine ⟨3, ?_⟩
  intro n
  rcases Nat.eq_zero_or_pos n with h0 | hpos
  · subst h0
    simp
  have hn0 : (0 : ℝ) < n := by exact_mod_cast hpos
  have hfne : n.factorial ≠ 0 := n.factorial_ne_zero
  -- (c) log n! as a sum over primes ≤ n
  have hfac : Real.log (n.factorial : ℝ)
      = ∑ p ∈ Nat.primesLE n, (n.factorial.factorization p : ℝ) * Real.log (p : ℝ) := by
    rw [Real.log_nat_eq_sum_factorization]
    refine Finsupp.sum_of_support_subset _ ?_ _ (fun i _ => by simp)
    intro p hp
    rw [Nat.support_factorization, Nat.mem_primeFactors] at hp
    exact Nat.mem_primesLE.mpr ⟨(Nat.Prime.dvd_factorial hp.1).mp hp.2.1, hp.1⟩
  -- (d) Legendre bounds on the exponent
  have hleg : ∀ p ∈ Nat.primesLE n,
      (n : ℝ) / p - 1 ≤ (n.factorial.factorization p : ℝ) ∧
        (n.factorial.factorization p : ℝ) ≤ (n : ℝ) / ((p : ℝ) - 1) := by
    intro p hp
    have hpp := (Nat.mem_primesLE.mp hp).2
    have hp2 : (2 : ℝ) ≤ p := by exact_mod_cast hpp.two_le
    have hp0 : (0 : ℝ) < p := by linarith
    constructor
    · have hd : p ^ (n / p) ∣ n.factorial := by
        have h1 : n.factorial.factorization p ≥ n / p := by
          have h2 := Nat.factorization_factorial_mul (n := n / p) hpp
          have h3 : (p * (n / p)).factorial ∣ n.factorial :=
            Nat.factorial_dvd_factorial (Nat.mul_div_le n p)
          have h4 := (Nat.factorization_le_iff_dvd (Nat.factorial_ne_zero _) hfne).mpr h3 p
          omega
        exact (hpp.pow_dvd_iff_le_factorization hfne).mpr h1
      have h1 : n / p ≤ n.factorial.factorization p :=
        (hpp.pow_dvd_iff_le_factorization hfne).mp hd
      have h2 : (n : ℝ) < ((n / p : ℕ) : ℝ) * p + p := by
        have : n < n / p * p + p := by
          have := Nat.div_add_mod n p
          have := Nat.mod_lt n hpp.pos
          nlinarith [Nat.mul_comm p (n / p)]
        exact_mod_cast this
      have h3 : ((n / p : ℕ) : ℝ) ≤ (n.factorial.factorization p : ℝ) := by exact_mod_cast h1
      rw [sub_le_iff_le_add, div_le_iff₀ hp0]
      nlinarith
    · have h1 : (p - 1) * n.factorial.factorization p ≤ n := by
        rw [← Nat.multiplicity_eq_factorization hpp hfne, hpp.sub_one_mul_multiplicity_factorial]
        exact Nat.sub_le _ _
      have h2 : ((p : ℝ) - 1) * (n.factorial.factorization p : ℝ) ≤ n := by
        have : (((p - 1 : ℕ) : ℝ)) * (n.factorial.factorization p : ℝ) ≤ n := by exact_mod_cast h1
        rwa [Nat.cast_sub hpp.one_le, Nat.cast_one] at this
      rw [le_div_iff₀ (by linarith)]
      linarith
  have hlogp : ∀ p ∈ Nat.primesLE n, 0 ≤ Real.log (p : ℝ) := fun p _ =>
    Real.log_natCast_nonneg p
  -- (e) Chebyshev
  have hθ : ∑ p ∈ Nat.primesLE n, Real.log (p : ℝ) ≤ Real.log 4 * n := by
    have h := Chebyshev.theta_le_log4_mul_x (x := (n : ℝ)) hn0.le
    rw [Chebyshev.theta_eq_sum_Icc, Nat.floor_natCast] at h
    refine le_trans (le_of_eq ?_) h
    refine Finset.sum_congr ?_ (fun _ _ => rfl)
    ext p
    simp [Nat.mem_primesLE]
  have hl4 : Real.log 4 ≤ 3 := by
    have := Real.log_le_sub_one_of_pos (show (0 : ℝ) < 4 by norm_num)
    linarith
  -- (f) upper bound
  have hup : (n : ℝ) * ∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ)
      ≤ (n : ℝ) * Real.log n + Real.log 4 * n := by
    have h1 : ∑ p ∈ Nat.primesLE n, ((n : ℝ) / p - 1) * Real.log (p : ℝ)
        ≤ Real.log (n.factorial : ℝ) := by
      rw [hfac]
      exact Finset.sum_le_sum fun p hp =>
        mul_le_mul_of_nonneg_right (hleg p hp).1 (hlogp p hp)
    have h2 : ∑ p ∈ Nat.primesLE n, ((n : ℝ) / p - 1) * Real.log (p : ℝ)
        = (n : ℝ) * ∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ)
          - ∑ p ∈ Nat.primesLE n, Real.log (p : ℝ) := by
      rw [Finset.mul_sum, ← Finset.sum_sub_distrib]
      exact Finset.sum_congr rfl fun p _ => by ring
    have h3 : Real.log (n.factorial : ℝ) ≤ (n : ℝ) * Real.log n := by
      rw [← Real.log_pow]
      exact Real.log_le_log (by exact_mod_cast n.factorial_pos)
        (by exact_mod_cast Nat.factorial_le_pow n)
    linarith
  -- (g) lower bound
  have hlo : (n : ℝ) * Real.log n - n
      ≤ (n : ℝ) * ∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ) + (n : ℝ) * 2 := by
    have h1 : Real.log (n.factorial : ℝ)
        ≤ ∑ p ∈ Nat.primesLE n, (n : ℝ) / ((p : ℝ) - 1) * Real.log (p : ℝ) := by
      rw [hfac]
      exact Finset.sum_le_sum fun p hp =>
        mul_le_mul_of_nonneg_right (hleg p hp).2 (hlogp p hp)
    have h2 : ∑ p ∈ Nat.primesLE n, (n : ℝ) / ((p : ℝ) - 1) * Real.log (p : ℝ)
        = (n : ℝ) * ∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ)
          + (n : ℝ) * ∑ p ∈ Nat.primesLE n, Real.log (p : ℝ) / ((p : ℝ) * ((p : ℝ) - 1)) := by
      rw [Finset.mul_sum, Finset.mul_sum, ← Finset.sum_add_distrib]
      refine Finset.sum_congr rfl fun p hp => ?_
      have hp2 : (2 : ℝ) ≤ p := by exact_mod_cast (Nat.mem_primesLE.mp hp).2.two_le
      have : (p : ℝ) - 1 ≠ 0 := by linarith
      have : (p : ℝ) ≠ 0 := by linarith
      field_simp
      ring
    have h3 : ∑ p ∈ Nat.primesLE n, Real.log (p : ℝ) / ((p : ℝ) * ((p : ℝ) - 1)) ≤ 2 := by
      have hsub : Nat.primesLE n ⊆ Finset.Icc 2 (n - 1 + 1) := by
        intro p hp
        have := Nat.mem_primesLE.mp hp
        have := this.2.two_le
        rw [Finset.mem_Icc]
        omega
      refine (Finset.sum_le_sum_of_subset_of_nonneg hsub fun m hm _ => ?_).trans ?_
      · have hm2 : (2 : ℝ) ≤ m := by exact_mod_cast (Finset.mem_Icc.mp hm).1
        exact div_nonneg (Real.log_natCast_nonneg m) (by nlinarith)
      · refine (htail (n - 1)).trans ?_
        have : 0 ≤ (Real.log ((n - 1 + 1 : ℕ) : ℝ) + 2) / ((n - 1 + 1 : ℕ) : ℝ) :=
          div_nonneg (by linarith [Real.log_natCast_nonneg (n - 1 + 1)]) (by positivity)
        linarith
    have h4 := mul_le_mul_of_nonneg_left h3 hn0.le
    linarith [hstir n]
  rw [abs_le]
  constructor
  · have : (n : ℝ) * (Real.log n - 3) ≤ (n : ℝ) * ∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ) := by
      linarith
    linarith [le_of_mul_le_mul_left this hn0]
  · have : (n : ℝ) * ∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ) ≤ (n : ℝ) * (Real.log n + 3) := by
      nlinarith
    linarith [le_of_mul_le_mul_left this hn0]
