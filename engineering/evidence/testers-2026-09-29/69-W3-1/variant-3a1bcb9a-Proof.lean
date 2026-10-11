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
  have hω : ∀ n : ℕ, ω n = n.primeFactors.card := fun n => by
    rw [ArithmeticFunction.cardDistinctFactors_apply, ← List.card_toFinset]; rfl
  have pow_le : ∀ k : ℕ, 2 * k ≤ 2 ^ k := by
    intro k
    rcases k with _ | m
    · simp
    · have := @Nat.lt_two_pow_self m
      rw [pow_succ]; omega
  have hω2 : ∀ n : ℕ, 2 * ω n ≤ n := by
    intro n
    rcases Nat.eq_zero_or_pos n with h0 | hpos
    · subst h0; rw [hω]; simp
    · have h1 : 2 ^ n.primeFactors.card ≤ ∏ p ∈ n.primeFactors, p :=
        Finset.pow_card_le_prod _ _ _ (fun p hp => (Nat.prime_of_mem_primeFactors hp).two_le)
      have h2 : ∏ p ∈ n.primeFactors, p ≤ n := Nat.le_of_dvd hpos (Nat.prod_primeFactors_dvd n)
      rw [hω]
      exact (pow_le _).trans (h1.trans h2)
  obtain ⟨a, ha⟩ : ∃ a : ℕ → ℝ, a = fun n => (ω n : ℝ) / n.factorial := ⟨_, rfl⟩
  rw [show (∑' n : ℕ, (ω n : ℝ) / n.factorial) = ∑' n, a n by rw [ha]]
  have fpos : ∀ n : ℕ, (0 : ℝ) < n.factorial := fun n => by exact_mod_cast Nat.factorial_pos n
  have a_nonneg : ∀ n, 0 ≤ a n := fun n => by
    simp only [ha]; exact div_nonneg (Nat.cast_nonneg _) (fpos n).le
  have a_le : ∀ n, a n ≤ (2 : ℝ) ^ n / n.factorial := fun n => by
    simp only [ha]
    rw [div_le_div_iff_of_pos_right (fpos n)]
    have h : ω n ≤ 2 ^ n := by have := hω2 n; have := @Nat.lt_two_pow_self n; omega
    exact_mod_cast h
  have hs : Summable a :=
    Summable.of_nonneg_of_le a_nonneg a_le (Real.summable_pow_div_factorial 2)
  rintro ⟨q, hq⟩
  obtain ⟨N, hN⟩ : ∃ N, N = q.den + 2 := ⟨_, rfl⟩
  have hN2 : (2 : ℝ) ≤ N := by have : 2 ≤ N := by omega
                               exact_mod_cast this
  have split := Summable.sum_add_tsum_nat_add (N + 1) hs
  obtain ⟨T, hT⟩ : ∃ T, T = ∑' i, a (i + (N + 1)) := ⟨_, rfl⟩
  have hg : Summable (fun i => a (i + (N + 1))) := (summable_nat_add_iff (N + 1)).mpr hs
  have hNF : (0 : ℝ) < N.factorial := fpos N
  obtain ⟨r, hr⟩ : ∃ r : ℝ, r = 1 / ((N : ℝ) + 1) := ⟨_, rfl⟩
  have r0 : 0 ≤ r := by rw [hr]; positivity
  have r3 : r ≤ 1 / 3 := by rw [hr]; exact one_div_le_one_div_of_le (by norm_num) (by linarith)
  have r1 : r < 1 := by linarith
  -- each tail term, times N!, is at most (1/2) r^i
  have term : ∀ i, (N.factorial : ℝ) * a (i + (N + 1)) ≤ (1 / 2) * r ^ i := by
    intro i
    have hnat : N.factorial * ω (i + (N + 1)) * (2 * (N + 1) ^ i) ≤ (i + (N + 1)).factorial := by
      have h1 : 2 * ω (i + (N + 1)) ≤ N + i + 1 := by have := hω2 (i + (N + 1)); omega
      have h2 : N.factorial * (N + 1) ^ i ≤ (N + i).factorial := Nat.factorial_mul_pow_le_factorial
      have h3 : (i + (N + 1)).factorial = (N + i + 1) * (N + i).factorial := by
        rw [show i + (N + 1) = (N + i) + 1 by ring]; exact Nat.factorial_succ _
      rw [h3]
      calc N.factorial * ω (i + (N + 1)) * (2 * (N + 1) ^ i)
          = (2 * ω (i + (N + 1))) * (N.factorial * (N + 1) ^ i) := by ring
        _ ≤ (N + i + 1) * (N + i).factorial := Nat.mul_le_mul h1 h2
    have hreal : (N.factorial : ℝ) * ω (i + (N + 1)) * (2 * ((N : ℝ) + 1) ^ i)
        ≤ (i + (N + 1)).factorial := by exact_mod_cast hnat
    simp only [ha]
    rw [hr, one_div_pow, one_div_mul_one_div, mul_div_assoc',
      div_le_div_iff₀ (fpos _) (by positivity), one_mul]
    exact hreal
  have geo : Summable (fun i : ℕ => (1 / 2 : ℝ) * r ^ i) :=
    (summable_geometric_of_lt_one r0 r1).mul_left _
  have hTle : (N.factorial : ℝ) * T ≤ (1 / 2) * (1 - r)⁻¹ := by
    rw [hT, ← tsum_mul_left, ← tsum_geometric_of_lt_one r0 r1, ← tsum_mul_left]
    exact Summable.tsum_le_tsum term (hg.mul_left _) geo
  have hlt : (1 / 2 : ℝ) * (1 - r)⁻¹ < 1 := by
    have h1 : (2 / 3 : ℝ) ≤ 1 - r := by linarith
    have h2 : (1 - r)⁻¹ ≤ (2 / 3 : ℝ)⁻¹ := inv_anti₀ (by norm_num) h1
    calc (1 / 2 : ℝ) * (1 - r)⁻¹ ≤ 1 / 2 * (2 / 3 : ℝ)⁻¹ :=
          mul_le_mul_of_nonneg_left h2 (by norm_num)
      _ < 1 := by norm_num
  -- the tail is positive: omega (N + 1) ≥ 1
  have hTpos : 0 < T := by
    rw [hT]
    refine hg.tsum_pos (fun i => a_nonneg _) 0 ?_
    simp only [ha, zero_add]
    apply div_pos _ (fpos _)
    have : 0 < ω (N + 1) := ArithmeticFunction.cardDistinctFactors_pos.mpr (by omega)
    exact_mod_cast this
  -- N! times the finite part is an integer
  obtain ⟨Z, hZ⟩ : ∃ Z : ℕ,
      Z = ∑ i ∈ Finset.range (N + 1), ω i * (N.factorial / i.factorial) := ⟨_, rfl⟩
  have hZ' : (N.factorial : ℝ) * ∑ i ∈ Finset.range (N + 1), a i = Z := by
    rw [hZ, Finset.mul_sum, Nat.cast_sum]
    apply Finset.sum_congr rfl
    intro i hi
    have hi' : i ≤ N := Nat.lt_succ_iff.mp (Finset.mem_range.mp hi)
    rw [Nat.cast_mul, Nat.cast_div (Nat.factorial_dvd_factorial hi') (fpos i).ne']
    simp only [ha]; ring
  -- N! times q is an integer
  have hden : q.den ∣ N.factorial := Nat.dvd_factorial q.den_pos (by omega)
  have hM : (N.factorial : ℝ) * q = ((q.num * ((N.factorial / q.den : ℕ) : ℤ) : ℤ) : ℝ) := by
    rw [Int.cast_mul, Int.cast_natCast, Nat.cast_div hden (Nat.cast_ne_zero.mpr q.den_nz),
      Rat.cast_def]
    ring
  have key : (N.factorial : ℝ) * T
      = (((q.num * ((N.factorial / q.den : ℕ) : ℤ)) - Z : ℤ) : ℝ) := by
    rw [Int.cast_sub, ← hM, hq, ← split, ← hT, mul_add, hZ']
    push_cast; ring
  have i1 : (0 : ℤ) < q.num * ((N.factorial / q.den : ℕ) : ℤ) - Z := by
    have h : (0 : ℝ) < (N.factorial : ℝ) * T := mul_pos hNF hTpos
    rw [key] at h; exact_mod_cast h
  have i2 : q.num * ((N.factorial / q.den : ℕ) : ℤ) - Z < 1 := by
    have h : (N.factorial : ℝ) * T < 1 := lt_of_le_of_lt hTle hlt
    rw [key] at h; exact_mod_cast h
  omega
