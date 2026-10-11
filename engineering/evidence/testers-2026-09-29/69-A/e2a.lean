import Mathlib

open scoped ArithmeticFunction.omega

-- piece 1: the tail formula
example (f : ℕ → ℕ) (hs : Summable (fun n : ℕ => (f n : ℝ) / 2 ^ n)) (n : ℕ) :
    ∑' j : ℕ, (f (n + 1 + j) : ℝ) / 2 ^ (j + 1)
      = 2 ^ n * ∑' m : ℕ, (f m : ℝ) / 2 ^ m
        - ((∑ i ∈ Finset.range (n + 1), f i * 2 ^ (n - i) : ℕ) : ℝ) := by
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
