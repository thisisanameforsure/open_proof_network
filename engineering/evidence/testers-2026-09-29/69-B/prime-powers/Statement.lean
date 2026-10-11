import Mathlib
import Nodes.«variant-b43dd702».Context

/-! A related variant of Erdős problem 69 (D-30, relation `related`): the binary number whose
n-th digit is 1 exactly when `ω n = 1`, that is when n is a prime power, is irrational.

Why it sits beside erdos-69: the root sums `ω(n)/2^n`; this sums the indicator of the level set
`ω(n) = 1`, the first slice of that series (the prime powers, where `ω` counts one prime). Its
method is the one `variant-09e95e7a` uses for the primes, with a window that also avoids prime
powers: with `F = (k+1)!`, each of `F² + 2, …, F² + k + 1` is `j · (t·F + 1)` with `2 ≤ j ≤ k+1`
and `F = j·t`, and a prime of `j` divides `F` while a prime of `t·F + 1` does not, so each has
two distinct prime factors. It is not progress on the root, whose digits are not a 0/1 sequence
and have no such window of zeros. -/

open scoped ArithmeticFunction.omega

theorem Opn.erdos_69_prime_power_indicator :
    Irrational (∑' n : ℕ, if ω n = 1 then (1 / 2 : ℝ) ^ n else 0) := by
  sorry
