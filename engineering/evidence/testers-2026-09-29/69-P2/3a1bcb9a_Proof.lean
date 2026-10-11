import Mathlib
import Nodes.«variant-3a1bcb9a».Context

/-! A related variant of Erdős problem 69 (D-30, relation `related`): the root's digits `ω(n)`
written in the factorial base instead of base 2, `∑ ω(n)/n!`, give an irrational number.

Why it sits beside erdos-69: it keeps the root's own digits, `ω(n)`, and changes only the
weights, `2^{-n}` to `1/n!`. Method, the one for `e`: `2ω(n) ≤ n` (since `2^{ω(n)} ≤ n`), so
if the sum were `a/q`, then for `N = q + 2` the number `N!·(sum)` minus the integer
`∑_{n ≤ N} ω(n)·N!/n!` is `N!·(tail)`, which is positive (`ω(N+1) ≥ 1`) and at most
`(1/2)·∑_i (N+1)^{-i} = (N+1)/(2N) < 1`. The same bound fails for base 2, where the digits
`ω(n)` are unbounded against a fixed ratio: that is why the root is hard and this is not. -/

open scoped ArithmeticFunction.omega

theorem Opn.erdos_69_factorial_base :
    Irrational (∑' n : ℕ, (ω n : ℝ) / n.factorial) := by
  have hω : ∀ n : ℕ, ω n = n.primeFactors.card := fun n => rfl
  have h2ω : ∀ n : ℕ, 2 * ω n ≤ n := by
    intro n
    rcases Nat.eq_zero_or_pos n with rfl | hn
    · simp
    have hpow : 2 ^ ω n ≤ n := by
      rw [hω]
      calc 2 ^ n.primeFactors.card ≤ ∏ p ∈ n.primeFactors, p :=
            Finset.pow_card_le_prod _ _ _
              (fun p hp => (Nat.prime_of_mem_primeFactors hp).two_le)
        _ ≤ n := Nat.le_of_dvd hn (Nat.prod_primeFactors_dvd n)
    have hk : ∀ k : ℕ, 2 * k ≤ 2 ^ k := by
      intro k
      induction k with
      | zero => simp
      | succ k ih =>
        rcases Nat.eq_zero_or_pos k with rfl | hk
        · norm_num
        · rw [pow_succ]; omega
    exact (hk _).trans hpow
  have hω1 : ∀ n : ℕ, 2 ≤ n → 1 ≤ ω n := by
    intro n hn
    rw [hω]
    exact Finset.card_pos.mpr (Nat.nonempty_primeFactors.mpr hn)
  have hf0 : ∀ n : ℕ, 0 ≤ (ω n : ℝ) / n.factorial := fun n => by positivity
  have hsum : Summable (fun n : ℕ => (ω n : ℝ) / n.factorial) := by
    refine Summable.of_nonneg_of_le hf0 (fun n => ?_) (Real.summable_pow_div_factorial 2)
    have h1 : ω n ≤ 2 ^ n := by
      have := h2ω n
      have h2 : n < 2 ^ n := Nat.lt_two_pow_self
      omega
    have h1' : (ω n : ℝ) ≤ 2 ^ n := by exact_mod_cast h1
    exact div_le_div_of_nonneg_right h1' (by positivity)
  rintro ⟨q, hq⟩
  set N : ℕ := max q.den 2 with hN
  have hN2 : 2 ≤ N := le_max_right _ _
  have hNd : q.den ≤ N := le_max_left _ _
  have hsplit := hsum.sum_add_tsum_nat_add (N + 1)
  have htsum : Summable (fun k : ℕ => (ω (k + (N + 1)) : ℝ) / (k + (N + 1)).factorial) :=
    (summable_nat_add_iff (N + 1)).mpr hsum
  have hFpos : (0 : ℝ) < N.factorial := by positivity
  -- the rescaled tail is an integer
  obtain ⟨z, hz⟩ : ∃ z : ℤ,
      (N.factorial : ℝ) * ∑' k : ℕ, (ω (k + (N + 1)) : ℝ) / (k + (N + 1)).factorial = z := by
    obtain ⟨c, hc⟩ : q.den ∣ N.factorial := Nat.dvd_factorial q.den_pos hNd
    have hqN : (N.factorial : ℝ) * (q : ℝ) = ((q.num * c : ℤ) : ℝ) := by
      have hq' : (q : ℝ) = (q.num : ℝ) / (q.den : ℝ) := by
        rw [Rat.cast_def]
      have hden : (q.den : ℝ) ≠ 0 := by exact_mod_cast q.den_pos.ne'
      rw [hq', hc]
      push_cast
      field_simp
    have hfin : ∀ n ∈ Finset.range (N + 1), ∃ m : ℕ,
        (N.factorial : ℝ) * ((ω n : ℝ) / n.factorial) = ((ω n * m : ℕ) : ℝ) := by
      intro n hn
      obtain ⟨m, hm⟩ := Nat.factorial_dvd_factorial (Nat.lt_succ_iff.mp (Finset.mem_range.mp hn))
      refine ⟨m, ?_⟩
      rw [hm]
      push_cast
      have : (n.factorial : ℝ) ≠ 0 := by positivity
      field_simp
    choose! m hm using hfin
    refine ⟨q.num * c - ∑ n ∈ Finset.range (N + 1), ((ω n * m n : ℕ) : ℤ), ?_⟩
    have hR : (N.factorial : ℝ) * ∑' k : ℕ, (ω (k + (N + 1)) : ℝ) / (k + (N + 1)).factorial
        = (N.factorial : ℝ) * (q : ℝ)
          - ∑ n ∈ Finset.range (N + 1), (N.factorial : ℝ) * ((ω n : ℝ) / n.factorial) := by
      rw [hq, ← hsplit, mul_add, Finset.mul_sum]
      ring
    rw [hR, hqN, Finset.sum_congr rfl hm]
    push_cast
    ring
  -- positive
  have hpos : (0 : ℝ) < (N.factorial : ℝ) *
      ∑' k : ℕ, (ω (k + (N + 1)) : ℝ) / (k + (N + 1)).factorial := by
    refine mul_pos hFpos ?_
    refine htsum.tsum_pos (fun k => hf0 _) 0 ?_
    have : 1 ≤ ω (0 + (N + 1)) := hω1 _ (by omega)
    have : (1 : ℝ) ≤ ω (0 + (N + 1)) := by exact_mod_cast this
    positivity
  -- below one
  have hr0 : (0 : ℝ) ≤ 1 / ((N : ℝ) + 1) := by positivity
  have hr1 : 1 / ((N : ℝ) + 1) < 1 := by
    rw [div_lt_one (by positivity)]
    have : (2 : ℝ) ≤ N := by exact_mod_cast hN2
    linarith
  have hterm : ∀ k : ℕ, (N.factorial : ℝ) * ((ω (k + (N + 1)) : ℝ) / (k + (N + 1)).factorial)
      ≤ 1 / 2 * (1 / ((N : ℝ) + 1)) ^ k := by
    intro k
    have hωk : (2 : ℝ) * ω (k + (N + 1)) ≤ (k + (N + 1) : ℕ) := by exact_mod_cast h2ω _
    have hfac : ((N + k).factorial : ℝ) * ((k + (N + 1) : ℕ) : ℝ)
        = (k + (N + 1)).factorial := by
      rw [show k + (N + 1) = (N + k) + 1 by ring, Nat.factorial_succ]
      push_cast
      ring
    have hgrow : (N.factorial : ℝ) * ((N : ℝ) + 1) ^ k ≤ (N + k).factorial := by
      exact_mod_cast Nat.factorial_mul_pow_le_factorial
    have hNk : (0 : ℝ) < (N + k).factorial := by positivity
    have hnpos : (0 : ℝ) < ((k + (N + 1) : ℕ) : ℝ) := by positivity
    have hpk : (0 : ℝ) < ((N : ℝ) + 1) ^ k := by positivity
    rw [← hfac, div_pow, one_pow]
    rw [mul_div_assoc', div_le_iff₀ (by positivity)]
    calc (N.factorial : ℝ) * ω (k + (N + 1))
        ≤ (N.factorial : ℝ) * (((k + (N + 1) : ℕ) : ℝ) / 2) := by
          gcongr; linarith
      _ = 1 / 2 * (1 / ((N : ℝ) + 1) ^ k) * ((N.factorial : ℝ) * ((N : ℝ) + 1) ^ k)
            * ((k + (N + 1) : ℕ) : ℝ) := by
          field_simp
      _ ≤ 1 / 2 * (1 / ((N : ℝ) + 1) ^ k) * ((N + k).factorial : ℝ)
            * ((k + (N + 1) : ℕ) : ℝ) := by
          gcongr
      _ = 1 / 2 * (1 / ((N : ℝ) + 1) ^ k) * (((N + k).factorial : ℝ) * ((k + (N + 1) : ℕ) : ℝ)) := by
          ring
  have hgeo : Summable (fun k : ℕ => 1 / 2 * (1 / ((N : ℝ) + 1)) ^ k) :=
    (summable_geometric_of_lt_one hr0 hr1).mul_left _
  have hlt : (N.factorial : ℝ) *
      ∑' k : ℕ, (ω (k + (N + 1)) : ℝ) / (k + (N + 1)).factorial < 1 := by
    rw [← tsum_mul_left]
    calc ∑' k : ℕ, (N.factorial : ℝ) * ((ω (k + (N + 1)) : ℝ) / (k + (N + 1)).factorial)
        ≤ ∑' k : ℕ, 1 / 2 * (1 / ((N : ℝ) + 1)) ^ k :=
          (htsum.mul_left _).tsum_le_tsum hterm hgeo
      _ = 1 / 2 * (1 - 1 / ((N : ℝ) + 1))⁻¹ := by
          rw [tsum_mul_left, tsum_geometric_of_lt_one hr0 hr1]
      _ < 1 := by
          have hN' : (2 : ℝ) ≤ N := by exact_mod_cast hN2
          have h1 : 1 - 1 / ((N : ℝ) + 1) = (N : ℝ) / ((N : ℝ) + 1) := by
            field_simp; ring
          rw [h1, inv_div]
          rw [show 1 / 2 * (((N : ℝ) + 1) / N) = ((N : ℝ) + 1) / (2 * N) by ring]
          rw [div_lt_one (by positivity)]
          linarith
  rw [hz] at hpos hlt
  have h0 : (0 : ℤ) < z := by exact_mod_cast hpos
  have h1 : z < 1 := by exact_mod_cast hlt
  omega
