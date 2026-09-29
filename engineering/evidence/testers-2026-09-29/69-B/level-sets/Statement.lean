import Mathlib
import Nodes.«variant-14c6c771».Context

/-! A related variant of Erdős problem 69 (D-30, relation `related`): for every `m ≥ 1`, the
binary number whose n-th digit is 1 exactly when `ω n = m` is irrational.

Why it sits beside erdos-69: the root's number is `∑ ω(n)/2^n = ∑_{m ≥ 1} m · x_m`, where `x_m`
is the binary number of the level set `ω = m`; this node proves every `x_m` irrational. (`m = 0`
is excluded because `ω n = 0` only for `n = 0, 1`, giving `3/2`.) Method: by the Chinese
remainder theorem, for any `k` there are `k` consecutive integers each divisible by `m + 1`
fixed primes of its own, so each has `ω ≥ m + 1`: a window of `k` zero digits; and the powers
of a product of `m` primes give infinitely many 1 digits. If `x_m = a/k` then `k · 2^N · (tail
after the window)` is an integer strictly between 0 and 1. It does not reach the root: an
irrational combination of irrationals can be rational, and the root's digits have no window of
zeros. -/

open scoped ArithmeticFunction.omega

theorem Opn.erdos_69_omega_level_sets :
    ∀ m : ℕ, 1 ≤ m → Irrational (∑' n : ℕ, if ω n = m then (1 / 2 : ℝ) ^ n else 0) := by
  sorry
