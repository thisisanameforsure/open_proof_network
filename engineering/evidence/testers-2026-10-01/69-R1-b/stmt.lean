import Mathlib
theorem Opn.erdos_69_mertens_reciprocal_primes :
    ∃ C : ℝ, 0 ≤ C ∧ ∀ x : ℕ, 2 ≤ x →
      |∑ p ∈ Nat.primesLE x, (1 : ℝ) / p - Real.log (Real.log (x : ℝ))| ≤ C := by
  sorry
theorem Opn.erdos_69_mertens_log_weighted :
    ∃ C : ℝ, ∀ n : ℕ, 1 ≤ n →
      |∑ p ∈ Nat.primesLE n, Real.log p / (p : ℝ) - Real.log n| ≤ C := by
  sorry
