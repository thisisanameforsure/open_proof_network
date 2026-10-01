import Mathlib

open scoped ArithmeticFunction.omega

theorem omega_window :
    ∀ (k : ℕ) (c : ℕ → ℕ), ∃ N : ℕ, ∀ j < k, c j ≤ ω (N + 1 + j) := by
  have hω : ∀ x : ℕ, ω x = x.primeFactors.card := fun x => by
    rw [ArithmeticFunction.cardDistinctFactors_apply]; rfl
  have hmono : ∀ d x : ℕ, d ∣ x → x ≠ 0 → ω d ≤ ω x := by
    intro d x hd hx
    rw [hω, hω]
    exact Finset.card_le_card (Nat.primeFactors_mono hd hx)
  -- a modulus coprime to M carrying at least c distinct primes
  have hQ : ∀ M c : ℕ, 0 < M → ∃ Q : ℕ, 0 < Q ∧ Nat.Coprime M Q ∧ c ≤ ω Q := by
    intro M c hM
    induction c with
    | zero => exact ⟨1, one_pos, Nat.coprime_one_right M, Nat.zero_le _⟩
    | succ c ih =>
      obtain ⟨Q, hQpos, hcop, hc⟩ := ih
      have hne : M * Q + 1 ≠ 1 := by
        have : 0 < M * Q := Nat.mul_pos hM hQpos
        omega
      set p := (M * Q + 1).minFac with hp_def
      have hp : p.Prime := Nat.minFac_prime hne
      have hpdvd : p ∣ M * Q + 1 := Nat.minFac_dvd _
      have hpMQ : ¬ p ∣ M * Q := by
        intro h
        have : p ∣ 1 := (Nat.dvd_add_right h).mp hpdvd
        exact hp.one_lt.ne' (Nat.dvd_one.mp this)
      have hpM : ¬ p ∣ M := fun h => hpMQ (Dvd.dvd.mul_right h Q)
      have hpQ : ¬ p ∣ Q := fun h => hpMQ (Dvd.dvd.mul_left h M)
      have hcopQp : Nat.Coprime Q p := ((Nat.Prime.coprime_iff_not_dvd hp).mpr hpQ).symm
      refine ⟨Q * p, Nat.mul_pos hQpos hp.pos, ?_, ?_⟩
      · exact Nat.Coprime.mul_right hcop ((Nat.Prime.coprime_iff_not_dvd hp).mpr hpM).symm
      · rw [ArithmeticFunction.cardDistinctFactors_mul hcopQp,
          show p = p ^ 1 from (pow_one p).symm,
          ArithmeticFunction.cardDistinctFactors_apply_prime_pow hp one_ne_zero]
        omega
  intro k c
  induction k with
  | zero => exact ⟨0, fun j hj => absurd hj (Nat.not_lt_zero _)⟩
  | succ k ih =>
    obtain ⟨N, hN⟩ := ih
    set M := ∏ j ∈ Finset.range k, (N + 1 + j) with hM_def
    have hMpos : 0 < M := Finset.prod_pos (fun j _ => by omega)
    obtain ⟨Q, hQpos, hcop, hcQ⟩ := hQ M (c k) hMpos
    set r := Q - (N + 1 + k) % Q with hr
    obtain ⟨x, hx0, hxr⟩ := Nat.chineseRemainder hcop 0 r
    have hMx : M ∣ x := Nat.modEq_zero_iff_dvd.mp hx0
    refine ⟨N + x, fun j hj => ?_⟩
    rcases Nat.lt_succ_iff_lt_or_eq.mp hj with hj | hj
    · -- old positions keep their prime factors
      have hdM : N + 1 + j ∣ M := Finset.dvd_prod_of_mem (fun j => N + 1 + j) (Finset.mem_range.mpr hj)
      have hd : N + 1 + j ∣ N + x + 1 + j := by
        rw [show N + x + 1 + j = (N + 1 + j) + x by ring]
        exact Nat.dvd_add_self_left.mpr (hdM.trans hMx)
      exact (hN j hj).trans (hmono _ _ hd (by omega))
    · -- the new position is divisible by Q
      subst hj
      have hsum : Q ∣ (N + 1 + j) + r := by
        have h1 := Nat.div_add_mod (N + 1 + j) Q
        have h2 := Nat.mod_lt (N + 1 + j) hQpos
        refine ⟨(N + 1 + j) / Q + 1, ?_⟩
        rw [hr, mul_add, mul_one]
        generalize Q * ((N + 1 + j) / Q) = u at *
        omega
      have hmod : (N + 1 + j) + x ≡ 0 [MOD Q] :=
        (Nat.ModEq.add_left (N + 1 + j) hxr).trans (Nat.modEq_zero_iff_dvd.mpr hsum)
      have hdQ : Q ∣ N + x + 1 + j := by
        rw [show N + x + 1 + j = (N + 1 + j) + x by ring]
        exact Nat.modEq_zero_iff_dvd.mp hmod
      exact hcQ.trans (hmono _ _ hdQ (by omega))
