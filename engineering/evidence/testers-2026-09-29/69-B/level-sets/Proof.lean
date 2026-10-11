import Mathlib
import Nodes.«variant-14c6c771».Context

/-! A related variant of Erdős problem 69 (D-30, relation `related`): for every `m ≥ 1`, the
binary number whose n-th digit is 1 exactly when `ω n = m` is irrational.

Why it sits beside erdos-69: the root's number is `∑ ω(n)/2^n = ∑_{m ≥ 1} m · x_m`, where `x_m`
is the binary number of the level set `ω = m`; this node proves every `x_m` irrational. (`m = 0`
is excluded because `ω n = 0` only for `n = 0, 1`, giving `3/2`.) Method: by the Chinese
remainder theorem, for any `k` there are `k` consecutive integers each divisible by `m + 1`
fixed primes of its own, so each has `ω ≥ m + 1`: a window of `k` zero digits; and the powers
of a product of `m` primes give infinitely many 1 digits. If `x_m = a/k` then `k · 2^N · (tail
after the window)` is an integer strictly between 0 and 1. It does not reach the root: an
irrational combination of irrationals can be rational, and the root's digits have no window of
zeros. -/

open scoped ArithmeticFunction.omega

theorem Opn.erdos_69_omega_level_sets :
    ∀ m : ℕ, 1 ≤ m → Irrational (∑' n : ℕ, if ω n = m then (1 / 2 : ℝ) ^ n else 0) := by
  intro m hm
  have hω : ∀ n : ℕ, ω n = n.primeFactors.card := fun n => by
    rw [ArithmeticFunction.cardDistinctFactors_apply, ← List.card_toFinset]; rfl
  have Pinj : Function.Injective (Nat.nth Nat.Prime) := Nat.nth_injective Nat.infinite_setOfPred_prime
  -- `T j c`: the `c` primes with indices `(j, 0), …, (j, c - 1)`, disjoint for distinct `j`
  obtain ⟨T, hT⟩ : ∃ T : ℕ → ℕ → Finset ℕ, ∀ j c,
      T j c = (Finset.range c).image (fun i => Nat.nth Nat.Prime (Nat.pair j i)) :=
    ⟨fun j c => _, fun _ _ => rfl⟩
  have T_prime : ∀ j c, ∀ p ∈ T j c, p.Prime := by
    intro j c p hp
    rw [hT] at hp
    obtain ⟨i, -, rfl⟩ := Finset.mem_image.mp hp
    exact Nat.prime_nth_prime _
  have T_card : ∀ j c, (T j c).card = c := by
    intro j c
    rw [hT, Finset.card_image_of_injective _ (fun a b h => (Nat.pair_eq_pair.mp (Pinj h)).2),
      Finset.card_range]
  have T_disj : ∀ j j' c c', j ≠ j' → ∀ p ∈ T j c, ∀ q ∈ T j' c', p ≠ q := by
    intro j j' c c' hjj p hp q hq hpq
    rw [hT] at hp hq
    obtain ⟨i, -, rfl⟩ := Finset.mem_image.mp hp
    obtain ⟨i', -, rfl⟩ := Finset.mem_image.mp hq
    exact hjj (Nat.pair_eq_pair.mp (Pinj hpq)).1
  have prod_pf : ∀ j c, (∏ p ∈ T j c, p).primeFactors = T j c :=
    fun j c => Nat.primeFactors_prod (T_prime j c)
  -- `Q j`: a product of `m + 1` primes, pairwise coprime for distinct `j`
  obtain ⟨Q, hQ⟩ : ∃ Q : ℕ → ℕ, ∀ j, Q j = ∏ p ∈ T j (m + 1), p := ⟨fun j => _, fun _ => rfl⟩
  have Qpos : ∀ j, 0 < Q j := fun j => by
    rw [hQ]; exact Finset.prod_pos (fun p hp => (T_prime j (m + 1) p hp).pos)
  have Qcop : ∀ j j', j ≠ j' → Nat.Coprime (Q j) (Q j') := by
    intro j j' hjj
    rw [hQ j, hQ j']
    apply Nat.Coprime.prod_left
    intro p hp
    apply Nat.Coprime.prod_right
    intro q hq
    exact (Nat.coprime_primes (T_prime _ _ p hp) (T_prime _ _ q hq)).mpr
      (T_disj j j' _ _ hjj p hp q hq)
  -- a window of `k` places, each with at least `m + 1` prime factors (Chinese remainder theorem)
  have window : ∀ k : ℕ, ∃ N : ℕ, ∀ j, j < k → ω (j + (N + 1)) ≠ m := by
    intro k
    obtain ⟨N, hN⟩ := Nat.chineseRemainderOfFinset (fun j => Q j - (j + 1) % Q j) Q
      (Finset.range k) (fun j _ => (Qpos j).ne') (fun j _ j' _ hjj => Qcop j j' hjj)
    refine ⟨N, fun j hj => ?_⟩
    have hmod := hN j (Finset.mem_range.mpr hj)
    have hdvd : Q j ∣ j + (N + 1) := by
      have h1 : N + (j + 1) ≡ (Q j - (j + 1) % Q j) + (j + 1) % Q j [MOD Q j] :=
        Nat.ModEq.add hmod (Nat.mod_modEq (j + 1) (Q j)).symm
      rw [Nat.sub_add_cancel (Nat.mod_lt _ (Qpos j)).le] at h1
      have h2 : N + (j + 1) ≡ 0 [MOD Q j] := h1.trans (Nat.modEq_zero_iff_dvd.mpr dvd_rfl)
      have h3 := Nat.modEq_zero_iff_dvd.mp h2
      rwa [show j + (N + 1) = N + (j + 1) by ring]
    have hsub : T j (m + 1) ⊆ (j + (N + 1)).primeFactors := by
      rw [← prod_pf j (m + 1), ← hQ]
      exact Nat.primeFactors_mono hdvd (by omega)
    have hcard := Finset.card_le_card hsub
    rw [T_card] at hcard
    rw [hω]; omega
  -- infinitely many `n` with exactly `m` prime factors: the powers of a product of `m` primes
  obtain ⟨W, hW⟩ : ∃ W : ℕ, W = ∏ p ∈ T 0 m, p := ⟨_, rfl⟩
  have Wc : W.primeFactors.card = m := by rw [hW, prod_pf, T_card]
  have W2 : 2 ≤ W := by
    rcases Nat.lt_or_ge W 2 with h | h
    · interval_cases W <;> simp at Wc <;> omega
    · exact h
  have many : ∀ L : ℕ, ∃ n, L ≤ n ∧ ω n = m := by
    intro L
    refine ⟨W ^ (L + 1), ?_, ?_⟩
    · calc L ≤ 2 ^ L := Nat.lt_two_pow_self.le
        _ ≤ 2 ^ (L + 1) := Nat.pow_le_pow_right (by norm_num) (by omega)
        _ ≤ W ^ (L + 1) := Nat.pow_le_pow_left W2 _
    · rw [hω, Nat.primeFactors_pow _ (by omega), Wc]
  obtain ⟨b, hbdef⟩ : ∃ b : ℕ, b = 2 := ⟨_, rfl⟩
  have hb : 2 ≤ b := by omega
  have hb0 : (2 : ℝ) ≤ (b : ℝ) := by exact_mod_cast hb
  have bpos : (0 : ℝ) < b := by linarith
  obtain ⟨r, hr⟩ : ∃ r : ℝ, r = 1 / (b : ℝ) := ⟨_, rfl⟩
  have r0 : 0 < r := by rw [hr]; exact one_div_pos.mpr bpos
  have r2 : r ≤ 1 / 2 := by rw [hr]; exact one_div_le_one_div_of_le (by norm_num) hb0
  have rb : r * (b : ℝ) = 1 := by rw [hr, one_div, inv_mul_cancel₀ bpos.ne']
  have r12 : r = 1 / 2 := by rw [hr, hbdef]; norm_num
  obtain ⟨f, hf⟩ : ∃ f : ℕ → ℝ, f = fun n => if ω n = m then r ^ n else 0 := ⟨_, rfl⟩
  have hconv : (∑' n : ℕ, if ω n = m then (1 / 2 : ℝ) ^ n else 0) = ∑' n : ℕ, f n := by
    simp only [hf, r12]
  rw [hconv]
  have f_nonneg : ∀ n, 0 ≤ f n := fun n => by
    simp only [hf]; split_ifs
    · exact pow_nonneg r0.le n
    · exact le_rfl
  have f_le : ∀ n, f n ≤ r ^ n := fun n => by
    simp only [hf]; split_ifs
    · exact le_rfl
    · exact pow_nonneg r0.le n
  have hs : Summable f :=
    Summable.of_nonneg_of_le f_nonneg f_le
      (summable_geometric_of_lt_one r0.le (by linarith))
  rintro ⟨q, hq⟩
  obtain ⟨k, hk⟩ : ∃ k, k = q.den := ⟨_, rfl⟩
  have kpos : 0 < k := by rw [hk]; exact q.den_pos
  obtain ⟨N, hNw⟩ := window k
  have comp : ∀ j, j < k → f (j + (N + 1)) = 0 := by
    intro j hj
    simp only [hf]
    rw [if_neg (hNw j hj)]
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
  obtain ⟨R, hR⟩ : ∃ R, R = ∑' i, f (i + k + (N + 1)) := ⟨_, rfl⟩
  have split2' : ∑' i, f (i + (N + 1)) = R := by
    rw [← split2, zero_part, zero_add, hR]
  have Rpos : 0 < R := by
    obtain ⟨p, hp1, hp2⟩ := many (k + (N + 1))
    have hpi : p - (k + (N + 1)) + k + (N + 1) = p := by omega
    rw [hR]
    refine hg'.tsum_pos (fun i => f_nonneg _) (p - (k + (N + 1))) ?_
    rw [hpi]; simp only [hf, if_pos hp2]
    exact pow_pos r0 p
  have geo : Summable (fun i : ℕ => r ^ (k + (N + 1)) * (1 / 2 : ℝ) ^ i) :=
    summable_geometric_two.mul_left _
  have term_le : ∀ i, f (i + k + (N + 1)) ≤ r ^ (k + (N + 1)) * (1 / 2 : ℝ) ^ i := by
    intro i
    calc f (i + k + (N + 1)) ≤ r ^ (i + k + (N + 1)) := f_le _
      _ = r ^ (k + (N + 1)) * r ^ i := by ring
      _ ≤ r ^ (k + (N + 1)) * (1 / 2 : ℝ) ^ i :=
        mul_le_mul_of_nonneg_left (pow_le_pow_left₀ r0.le r2 i) (pow_nonneg r0.le _)
  have Rle : R ≤ r ^ (k + (N + 1)) * 2 := by
    rw [hR]
    calc ∑' i, f (i + k + (N + 1)) ≤ ∑' i : ℕ, r ^ (k + (N + 1)) * (1 / 2 : ℝ) ^ i :=
          Summable.tsum_le_tsum term_le hg' geo
      _ = r ^ (k + (N + 1)) * 2 := by rw [tsum_mul_left, tsum_geometric_two]
  have bN : (b : ℝ) ^ N * r ^ N = 1 := by rw [← mul_pow, mul_comm, rb, one_pow]
  have key : (b : ℝ) ^ N * (r ^ (k + (N + 1)) * 2) ≤ r ^ k := by
    have e : (b : ℝ) ^ N * (r ^ (k + (N + 1)) * 2)
        = r ^ k * ((b : ℝ) ^ N * r ^ N) * (2 * r) := by ring
    rw [e, bN, mul_one]
    have h2r : 2 * r ≤ 1 := by linarith
    calc r ^ k * (2 * r) ≤ r ^ k * 1 := mul_le_mul_of_nonneg_left h2r (pow_nonneg r0.le k)
      _ = r ^ k := mul_one _
  obtain ⟨Z, hZ⟩ : ∃ Z : ℕ,
      Z = ∑ i ∈ Finset.range (N + 1), if ω i = m then b ^ (N - i) else 0 := ⟨_, rfl⟩
  have hZ' : (b : ℝ) ^ N * ∑ i ∈ Finset.range (N + 1), f i = (Z : ℝ) := by
    rw [hZ, Finset.mul_sum]; push_cast
    apply Finset.sum_congr rfl
    intro i hi
    have hi' : i ≤ N := Nat.lt_succ_iff.mp (Finset.mem_range.mp hi)
    simp only [hf]
    split_ifs
    · have e : (b : ℝ) ^ N = (b : ℝ) ^ (N - i) * (b : ℝ) ^ i := by
        rw [← pow_add, Nat.sub_add_cancel hi']
      rw [e, mul_assoc, ← mul_pow, mul_comm (b : ℝ) r, rb, one_pow, mul_one]
    · simp
  have hqk : (q : ℝ) * k = q.num := by rw [hk]; exact_mod_cast Rat.mul_den_eq_num q
  have hx : (q : ℝ) = ∑ i ∈ Finset.range (N + 1), f i + R := by
    rw [hq, ← split1, split2']
  have hm : (((b : ℤ) ^ N * q.num - k * Z : ℤ) : ℝ) = (k : ℝ) * ((b : ℝ) ^ N * R) := by
    push_cast
    rw [← hqk, hx, ← hZ']; ring
  have kR : (0 : ℝ) < k := by exact_mod_cast kpos
  have mpos : (0 : ℝ) < (((b : ℤ) ^ N * q.num - k * Z : ℤ) : ℝ) := by
    rw [hm]; exact mul_pos kR (mul_pos (pow_pos bpos N) Rpos)
  have mlt : (((b : ℤ) ^ N * q.num - k * Z : ℤ) : ℝ) < 1 := by
    rw [hm]
    have h2 : (b : ℝ) ^ N * R ≤ r ^ k :=
      le_trans (mul_le_mul_of_nonneg_left Rle (pow_nonneg bpos.le N)) key
    have hk2 : (k : ℝ) < 2 ^ k := by exact_mod_cast Nat.lt_two_pow_self
    have hkb : (k : ℝ) * r ^ k < 1 := by
      have e : (k : ℝ) * r ^ k = k / (b : ℝ) ^ k := by rw [hr, div_pow, one_pow, mul_one_div]
      rw [e, div_lt_one (pow_pos bpos k)]
      calc (k : ℝ) < 2 ^ k := hk2
        _ ≤ (b : ℝ) ^ k := pow_le_pow_left₀ (by norm_num) hb0 k
    calc (k : ℝ) * ((b : ℝ) ^ N * R) ≤ k * r ^ k := mul_le_mul_of_nonneg_left h2 kR.le
      _ < 1 := hkb
  have i1 : (0 : ℤ) < (b : ℤ) ^ N * q.num - k * Z := by exact_mod_cast mpos
  have i2 : (b : ℤ) ^ N * q.num - k * Z < 1 := by exact_mod_cast mlt
  omega
