import Mathlib

open scoped ArithmeticFunction.omega

/-- ω on a product, without coprimality: the primes shared by a and n are
exactly the primes of gcd a n, so they are counted once, not twice. -/
theorem omega_mul_add_omega_gcd (a n : ℕ) (ha : a ≠ 0) (hn : n ≠ 0) :
    ω (a * n) + ω (Nat.gcd a n) = ω a + ω n := by
  have hω : ∀ m : ℕ, ω m = m.primeFactors.card := fun m => by
    rw [ArithmeticFunction.cardDistinctFactors_apply]; rfl
  rw [hω, hω, hω, hω, Nat.primeFactors_mul ha hn, Nat.primeFactors_gcd ha hn,
    Finset.card_union_add_card_inter]
