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
  sorry
