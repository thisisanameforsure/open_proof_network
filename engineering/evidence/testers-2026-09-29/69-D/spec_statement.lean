import Mathlib

open scoped ArithmeticFunction.omega

/-- The dilation identity for the tails of `∑ ω(n)/2^n` (Erdős 69): dilating by `a`
adds `ω a` and removes the mass of the primes of `a` dividing the shifted integers.
It is step (b) of the dilation route described in the annex of graph PR #256. -/
theorem Opn.erdos_69_dilated_tail :
    ∀ a m : ℕ, a ≠ 0 →
      ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
        = ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ)
          - ∑ p ∈ a.primeFactors,
              ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) := by
  sorry
