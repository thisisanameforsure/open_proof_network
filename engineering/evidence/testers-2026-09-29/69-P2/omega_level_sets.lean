import Mathlib

open scoped ArithmeticFunction.omega

theorem level_sets :
    ∀ m : ℕ, 1 ≤ m → Irrational (∑' n : ℕ, if ω n = m then (1 / 2 : ℝ) ^ n else 0) := by
  intro m hm1
  have hω : ∀ x : ℕ, ω x = x.primeFactors.card := fun x => by
    rw [ArithmeticFunction.cardDistinctFactors_apply]; rfl
  have hmono : ∀ d x : ℕ, d ∣ x → x ≠ 0 → ω d ≤ ω x := by
    intro d x hd hx
    rw [hω, hω]
    exact Finset.card_le_card (Nat.primeFactors_mono hd hx)
  -- a modulus coprime to M with exactly c distinct prime factors
  have hQ : ∀ M c : ℕ, 0 < M → ∃ Q : ℕ, 0 < Q ∧ Nat.Coprime M Q ∧ ω Q = c := by
    intro M c hM
    induction c with
    | zero => exact ⟨1, one_pos, Nat.coprime_one_right M, by simp⟩
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
  -- a window of k consecutive integers, each with at least c j distinct prime factors
  have hwin : ∀ (k : ℕ) (c : ℕ → ℕ), ∃ N : ℕ, ∀ j < k, c j ≤ ω (N + 1 + j) := by
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
      · have hdM : N + 1 + j ∣ M :=
          Finset.dvd_prod_of_mem (fun j => N + 1 + j) (Finset.mem_range.mpr hj)
        have hd : N + 1 + j ∣ N + x + 1 + j := by
          rw [show N + x + 1 + j = (N + 1 + j) + x by ring]
          exact Nat.dvd_add_self_left.mpr (hdM.trans hMx)
        exact (hN j hj).trans (hmono _ _ hd (by omega))
      · subst hj
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
        exact hcQ.symm.le.trans (hmono _ _ hdQ (by omega))
  set f : ℕ → ℝ := fun n => if ω n = m then (1 / 2 : ℝ) ^ n else 0 with hf
  have f_nonneg : ∀ n, 0 ≤ f n := fun n => by
    simp only [hf]; split_ifs <;> positivity
  have f_le : ∀ n, f n ≤ (1 / 2 : ℝ) ^ n := fun n => by
    simp only [hf]; split_ifs
    · exact le_rfl
    · positivity
  have hs : Summable f :=
    Summable.of_nonneg_of_le f_nonneg f_le
      (summable_geometric_of_lt_one (by norm_num) (by norm_num))
  rintro ⟨q, hq⟩
  set k := q.den with hk
  have kpos : 0 < k := q.den_pos
  obtain ⟨N, hNwin⟩ := hwin k (fun _ => m + 1)
  -- the k integers after N have more than m distinct prime factors
  have comp : ∀ j, j < k → f (j + (N + 1)) = 0 := by
    intro j hj
    simp only [hf]
    rw [if_neg]
    have := hNwin j hj
    rw [show j + (N + 1) = N + 1 + j by ring]
    omega
  -- infinitely many n with ω n = m: the powers of a number with exactly m prime factors
  obtain ⟨P, hPpos, -, hPm⟩ := hQ 1 m one_pos
  have hP2 : 2 ≤ P := by
    by_contra h
    have : P = 1 := by omega
    rw [this] at hPm
    simp at hPm
    omega
  have hg : Summable (fun i => f (i + (N + 1))) := (summable_nat_add_iff (N + 1)).mpr hs
  have hg' : Summable (fun i => f (i + k + (N + 1))) := by
    have := (summable_nat_add_iff k).mpr hg
    simpa [add_assoc] using this
  have split1 := Summable.sum_add_tsum_nat_add (N + 1) hs
  have split2 := Summable.sum_add_tsum_nat_add k hg
  have zero_part : ∑ i ∈ Finset.range k, f (i + (N + 1)) = 0 := by
    apply Finset.sum_eq_zero
    intro j hj
    exact comp j (Finset.mem_range.mp hj)
  set R := ∑' i, f (i + k + (N + 1)) with hR
  have split2' : ∑' i, f (i + (N + 1)) = R := by
    rw [← split2, zero_part, zero_add]
  -- R is positive
  have Rpos : 0 < R := by
    set e := k + (N + 1) with he
    have hbig : e < P ^ e :=
      lt_of_lt_of_le Nat.lt_two_pow_self (Nat.pow_le_pow_left hP2 e)
    have hωP : ω (P ^ e) = m := by
      rw [hω, Nat.primeFactors_pow P (by omega : e ≠ 0), ← hω, hPm]
    have hpi : P ^ e - e + k + (N + 1) = P ^ e := by omega
    refine hg'.tsum_pos (fun i => f_nonneg _) (P ^ e - e) ?_
    rw [hpi]; simp only [hf, if_pos hωP]; positivity
  -- R is small
  have geo : Summable (fun i : ℕ => (1 / 2 : ℝ) ^ (i + k + (N + 1))) := by
    have := (summable_nat_add_iff (k + (N + 1))).mpr
      (summable_geometric_of_lt_one (by norm_num : (0:ℝ) ≤ 1 / 2) (by norm_num))
    simpa [add_assoc] using this
  have Rle : R ≤ (1 / 2 : ℝ) ^ (k + (N + 1)) * 2 := by
    calc R ≤ ∑' i : ℕ, (1 / 2 : ℝ) ^ (i + k + (N + 1)) :=
          Summable.tsum_le_tsum (fun i => f_le _) hg' geo
      _ = (1 / 2 : ℝ) ^ (k + (N + 1)) * 2 := by
          simp_rw [add_assoc, pow_add]
          rw [tsum_mul_right, tsum_geometric_two, mul_comm]
  have key : (2 : ℝ) ^ N * ((1 / 2 : ℝ) ^ (k + (N + 1)) * 2) = (1 / 2) ^ k := by
    have h1 : (2 : ℝ) ^ N * (1 / 2) ^ N = 1 := by rw [← mul_pow]; norm_num
    calc (2 : ℝ) ^ N * ((1 / 2 : ℝ) ^ (k + (N + 1)) * 2)
        = (1 / 2) ^ k * ((2 : ℝ) ^ N * (1 / 2) ^ N) * ((1 / 2) * 2) := by
          rw [pow_add, pow_succ]; ring
      _ = (1 / 2) ^ k := by rw [h1]; norm_num
  -- the finite part times 2^N is an integer
  set Z : ℕ := ∑ i ∈ Finset.range (N + 1), if ω i = m then 2 ^ (N - i) else 0 with hZ
  have hZ' : (2 : ℝ) ^ N * ∑ i ∈ Finset.range (N + 1), f i = (Z : ℝ) := by
    rw [hZ, Finset.mul_sum]; push_cast
    apply Finset.sum_congr rfl
    intro i hi
    have hi' : i ≤ N := Nat.lt_succ_iff.mp (Finset.mem_range.mp hi)
    simp only [hf]
    split_ifs
    · have e : (2 : ℝ) ^ N = 2 ^ (N - i) * 2 ^ i := by
        rw [← pow_add, Nat.sub_add_cancel hi']
      rw [e, mul_assoc, ← mul_pow]; norm_num
    · simp
  have hqk : (q : ℝ) * k = q.num := by exact_mod_cast Rat.mul_den_eq_num q
  have hx : (q : ℝ) = ∑ i ∈ Finset.range (N + 1), f i + R := by
    rw [hq, ← split1, split2']
  have hm : ((2 ^ N * q.num - k * Z : ℤ) : ℝ) = (k : ℝ) * ((2 : ℝ) ^ N * R) := by
    push_cast
    rw [← hqk, hx, ← hZ']; ring
  have mpos : (0 : ℝ) < ((2 ^ N * q.num - k * Z : ℤ) : ℝ) := by
    rw [hm]; have : (0 : ℝ) < k := by exact_mod_cast kpos
    positivity
  have mlt : ((2 ^ N * q.num - k * Z : ℤ) : ℝ) < 1 := by
    rw [hm]
    have h2 : (2 : ℝ) ^ N * R ≤ (1 / 2) ^ k := by
      rw [← key]; exact mul_le_mul_of_nonneg_left Rle (by positivity)
    have hk2 : (k : ℝ) < 2 ^ k := by exact_mod_cast Nat.lt_two_pow_self
    have hk0 : (0 : ℝ) ≤ k := by positivity
    calc (k : ℝ) * ((2 : ℝ) ^ N * R) ≤ k * (1 / 2) ^ k := mul_le_mul_of_nonneg_left h2 hk0
      _ = k / 2 ^ k := by rw [one_div_pow, mul_one_div]
      _ < 1 := by rw [div_lt_one (by positivity)]; exact hk2
  have i1 : (0 : ℤ) < 2 ^ N * q.num - k * Z := by exact_mod_cast mpos
  have i2 : 2 ^ N * q.num - k * Z < (1 : ℤ) := by exact_mod_cast mlt
  omega
