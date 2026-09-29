import Mathlib

/-! A related variant of Erdős problem 69 (D-30, relation `related`): for every base `b ≥ 2`,
the number `∑_{p prime} b^{-p}`, whose base-`b` digits are 1 exactly at the prime places, is
irrational.

Why it sits beside erdos-69: it is the root's series `∑ ω(n)/2^n` with `ω(n)` replaced by the
prime indicator, and with the base 2 generalised to any `b ≥ 2`. The base-2 case is already
proved on this target as `variant-09e95e7a`; this statement is the strict generalisation, by
the same method: the `k` integers `(k+1)! + 2, …, (k+1)! + k + 1` are composite, so if the sum
were `a/k` the digits after place `N = (k+1)! + 1` would be zero for `k` places and not zero
for ever after, making `k · b^N · (tail)` an integer strictly between 0 and 1. It is not
progress on the root, whose hard part (the digits of `∑ ω(n)/2^n` are not eventually periodic)
this method does not reach. -/

theorem Opn.erdos_69_primes_any_base :
    ∀ b : ℕ, 2 ≤ b → Irrational (∑' p : Nat.Primes, (1 : ℝ) / (b : ℝ) ^ (p : ℕ)) := by
  intro b hb
  have hb0 : (2 : ℝ) ≤ (b : ℝ) := by exact_mod_cast hb
  have bpos : (0 : ℝ) < b := by linarith
  obtain ⟨r, hr⟩ : ∃ r : ℝ, r = 1 / (b : ℝ) := ⟨_, rfl⟩
  have r0 : 0 < r := by rw [hr]; exact one_div_pos.mpr bpos
  have r2 : r ≤ 1 / 2 := by rw [hr]; exact one_div_le_one_div_of_le (by norm_num) hb0
  have rb : r * (b : ℝ) = 1 := by rw [hr, one_div, inv_mul_cancel₀ bpos.ne']
  obtain ⟨f, hf⟩ : ∃ f : ℕ → ℝ, f = fun n => if n.Prime then r ^ n else 0 := ⟨_, rfl⟩
  have hconv : ∑' p : Nat.Primes, (1 : ℝ) / (b : ℝ) ^ (p : ℕ) = ∑' n : ℕ, f n := by
    have h := tsum_subtype {p : ℕ | p.Prime} (fun n : ℕ => (1 : ℝ) / (b : ℝ) ^ n)
    refine h.trans ?_
    congr 1; funext n
    simp only [Set.indicator_apply, Set.mem_ofPred_eq, hf, hr, one_div_pow]
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
  obtain ⟨N, hN⟩ : ∃ N, N = (k + 1).factorial + 1 := ⟨_, rfl⟩
  have comp : ∀ j, j < k → f (j + (N + 1)) = 0 := by
    intro j hj
    simp only [hf]
    rw [if_neg]
    intro hp
    have hd : (j + 2) ∣ j + (N + 1) := by
      have : (j + 2) ∣ (k + 1).factorial := Nat.dvd_factorial (by omega) (by omega)
      have e : j + (N + 1) = (k + 1).factorial + (j + 2) := by rw [hN]; ring
      rw [e]; exact dvd_add this dvd_rfl
    rcases hp.eq_one_or_self_of_dvd _ hd with h | h
    · omega
    · have : 0 < (k + 1).factorial := Nat.factorial_pos _
      rw [hN] at h; omega
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
    obtain ⟨p, hp1, hp2⟩ := Nat.exists_infinite_primes (k + (N + 1))
    have hpi : p - (k + (N + 1)) + k + (N + 1) = p := by omega
    rw [hR]
    refine hg'.tsum_pos (fun i => f_nonneg _) (p - (k + (N + 1))) ?_
    rw [hpi]; simp only [hf, if_pos hp2]; exact pow_pos r0 p
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
      Z = ∑ i ∈ Finset.range (N + 1), if i.Prime then b ^ (N - i) else 0 := ⟨_, rfl⟩
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
