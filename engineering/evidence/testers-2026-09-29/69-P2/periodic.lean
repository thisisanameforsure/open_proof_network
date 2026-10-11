import Mathlib

theorem rational_tails_periodic :
    ∀ (f : ℕ → ℕ) (q : ℚ), Summable (fun n : ℕ => (f n : ℝ) / 2 ^ n) →
      (q : ℝ) = ∑' n : ℕ, (f n : ℝ) / 2 ^ n →
      ∃ p N₀ : ℕ, 0 < p ∧ ∀ n n' : ℕ, N₀ ≤ n → N₀ ≤ n' → n ≡ n' [MOD p] →
        ∃ z : ℤ, ∑' j : ℕ, (f (n + 1 + j) : ℝ) / 2 ^ (j + 1)
          - ∑' j : ℕ, (f (n' + 1 + j) : ℝ) / 2 ^ (j + 1) = z := by
  intro f q hs hq
  -- every tail is 2^n q minus an integer
  have hT : ∀ n : ℕ, ∑' j : ℕ, (f (n + 1 + j) : ℝ) / 2 ^ (j + 1)
      = 2 ^ n * (q : ℝ) - ((∑ i ∈ Finset.range (n + 1), (f i : ℤ) * 2 ^ (n - i) : ℤ) : ℝ) := by
    intro n
    have h := hs.sum_add_tsum_nat_add (n + 1)
    have htail : ∑' j : ℕ, (f (j + (n + 1)) : ℝ) / 2 ^ (j + (n + 1))
        = (∑' j : ℕ, (f (n + 1 + j) : ℝ) / 2 ^ (j + 1)) / 2 ^ n := by
      rw [← tsum_div_const]
      congr 1
      funext j
      rw [show j + (n + 1) = n + 1 + j by ring, show n + 1 + j = (j + 1) + n by ring, pow_add]
      rw [show (j + 1) + n = n + 1 + j by ring]
      field_simp
    have hpow : ∀ i : ℕ, i ≤ n → (2 : ℝ) ^ (n - i) = 2 ^ n / 2 ^ i := fun i hi =>
      pow_sub₀ 2 (by norm_num) hi
    rw [hq, ← h, htail]
    push_cast
    have hs2 : ∑ i ∈ Finset.range (n + 1), (f i : ℝ) * 2 ^ (n - i)
        = 2 ^ n * ∑ i ∈ Finset.range (n + 1), (f i : ℝ) / 2 ^ i := by
      rw [Finset.mul_sum]
      refine Finset.sum_congr rfl (fun i hi => ?_)
      rw [hpow i (Nat.lt_succ_iff.mp (Finset.mem_range.mp hi))]
      ring
    rw [hs2]
    field_simp
    ring
  -- the denominator: 2^e times an odd b
  obtain ⟨e, b, hbodd, hden⟩ := Nat.exists_eq_two_pow_mul_odd q.den_nz
  have hbpos : 0 < b := hbodd.pos
  refine ⟨b.totient, e, Nat.totient_pos.mpr hbpos, ?_⟩
  intro n n' hn hn' hmod
  obtain ⟨u, rfl⟩ : ∃ u, n = u + e := ⟨n - e, by omega⟩
  obtain ⟨u', rfl⟩ : ∃ u', n' = u' + e := ⟨n' - e, by omega⟩
  have hu : u ≡ u' [MOD b.totient] := Nat.ModEq.add_right_cancel' e hmod
  -- 2^u ≡ 2^u' mod b
  have hcop : Nat.Coprime 2 b := Nat.coprime_two_left.mpr hbodd
  have hred : ∀ v : ℕ, 2 ^ v ≡ 2 ^ (v % b.totient) [MOD b] := by
    intro v
    conv_lhs => rw [← Nat.mod_add_div v b.totient, pow_add, pow_mul]
    have h1 : (2 ^ b.totient) ^ (v / b.totient) ≡ 1 ^ (v / b.totient) [MOD b] :=
      Nat.ModEq.pow _ (Nat.ModEq.pow_totient hcop)
    rw [one_pow] at h1
    simpa using Nat.ModEq.mul_left (2 ^ (v % b.totient)) h1
  have hpowmod : 2 ^ u' ≡ 2 ^ u [MOD b] := by
    have := (hred u').trans (hu ▸ (hred u).symm)
    exact this
  obtain ⟨t, ht⟩ := (Nat.modEq_iff_dvd.mp hpowmod)
  refine ⟨t * q.num - (∑ i ∈ Finset.range (u + e + 1), (f i : ℤ) * 2 ^ (u + e - i))
      + (∑ i ∈ Finset.range (u' + e + 1), (f i : ℤ) * 2 ^ (u' + e - i)), ?_⟩
  rw [hT, hT]
  have hqr : (q : ℝ) = (q.num : ℝ) / ((2 : ℝ) ^ e * b) := by
    rw [Rat.cast_def, hden]; push_cast; ring
  have htR : ((2 : ℝ) ^ u - 2 ^ u') = (b : ℝ) * t := by
    have := congrArg (fun z : ℤ => (z : ℝ)) ht
    push_cast at this
    linarith
  have hbR : (b : ℝ) ≠ 0 := by exact_mod_cast hbpos.ne'
  push_cast
  rw [hqr]
  field_simp
  rw [pow_add, pow_add]
  linear_combination (2 : ℝ) ^ e * (q.num : ℝ) * htR
