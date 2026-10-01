import Mathlib

open scoped ArithmeticFunction.omega

theorem Opn.erdos_69_omega_prime_sum :
    (∑' n, ω (n + 2) / 2 ^ (n + 2) : ℝ) = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1) := by
  sorry
