import Mathlib

open scoped ArithmeticFunction.omega

theorem Opn.probe_trap :
    ∑' n, ω (n + 2) / 2 ^ (n + 2) = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1) := by
  sorry
