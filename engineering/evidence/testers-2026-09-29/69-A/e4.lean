import Mathlib

open scoped ArithmeticFunction.omega

theorem Opn.erdos_69_rational_tails_lattice :
    ∀ (f : ℕ → ℕ) (q : ℚ), Summable (fun n : ℕ => (f n : ℝ) / 2 ^ n) →
      (q : ℝ) = ∑' n : ℕ, (f n : ℝ) / 2 ^ n →
      ∃ b : ℕ, 0 < b ∧ ∀ n : ℕ, ∃ z : ℤ,
        (b : ℝ) * ∑' j : ℕ, (f (n + 1 + j) : ℝ) / 2 ^ (j + 1) = z := by
  intro f q hs hq
  have htail : ∀ n : ℕ, ∑' j : ℕ, (f (n + 1 + j) : ℝ) / 2 ^ (j + 1)
      = 2 ^ n * ∑' m : ℕ, (f m : ℝ) / 2 ^ m
        - ((∑ i ∈ Finset.range (n + 1), f i * 2 ^ (n - i) : ℕ) : ℝ) := by
    intro n
    have h1 := Summable.sum_add_tsum_nat_add (n + 1) hs
    have h2 : ∀ j : ℕ, (f (j + (n + 1)) : ℝ) / 2 ^ (j + (n + 1))
        = (1 / 2 ^ n) * ((f (n + 1 + j) : ℝ) / 2 ^ (j + 1)) := by
      intro j
      rw [show j + (n + 1) = n + 1 + j by omega, show n + 1 + j = n + (j + 1) by omega, pow_add]
      field_simp
    rw [tsum_congr h2, tsum_mul_left] at h1
    have h3 : (2 : ℝ) ^ n * ∑ i ∈ Finset.range (n + 1), (f i : ℝ) / 2 ^ i
        = ((∑ i ∈ Finset.range (n + 1), f i * 2 ^ (n - i) : ℕ) : ℝ) := by
      push_cast
      rw [Finset.mul_sum]
      refine Finset.sum_congr rfl (fun i hi => ?_)
      have hi' : i ≤ n := Nat.lt_succ_iff.1 (Finset.mem_range.1 hi)
      have : (2 : ℝ) ^ n = 2 ^ (n - i) * 2 ^ i := by
        rw [← pow_add, Nat.sub_add_cancel hi']
      rw [this]
      field_simp
    rw [← h1, mul_add, h3, ← mul_assoc, mul_one_div_cancel (by positivity), one_mul]
    ring
  refine ⟨q.den, q.den_pos, fun n => ⟨2 ^ n * q.num
    - q.den * ((∑ i ∈ Finset.range (n + 1), f i * 2 ^ (n - i) : ℕ) : ℤ), ?_⟩⟩
  have hden : (q.den : ℝ) ≠ 0 := by exact_mod_cast q.den_nz
  rw [htail n, ← hq, Rat.cast_def]
  push_cast
  field_simp
