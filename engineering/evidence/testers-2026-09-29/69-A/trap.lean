import Mathlib

open scoped ArithmeticFunction.omega

example : (∑' n, ω (n + 2) / 2 ^ (n + 2) = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) ↔
    ((∑' n, ω (n + 2) / 2 ^ (n + 2) : ℝ) = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) := Iff.rfl
