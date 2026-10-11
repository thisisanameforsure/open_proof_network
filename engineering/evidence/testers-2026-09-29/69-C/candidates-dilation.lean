import Mathlib

open scoped ArithmeticFunction.omega

/-- E0: the composite-dilation identity (ω(a·n) = ω(a) + ω(n) − #{p ∣ a : p ∣ n}, summed with
binary weights). Unconditional and about ω alone. -/
theorem erdos69_dilated_tail (a m : ℕ) (ha : a ≠ 0) :
    ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
      = ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ)
        - ∑ p ∈ a.primeFactors,
            ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) := by
  sorry

/-- E0': the pointwise identity behind it. -/
theorem erdos69_omega_mul (a n : ℕ) (ha : a ≠ 0) (hn : n ≠ 0) :
    ω (a * n) + (a.primeFactors.filter (· ∣ n)).card = ω a + ω n := by
  sorry
