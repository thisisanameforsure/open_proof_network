import Mathlib

/-- Mertens' second theorem, bounded-error form: the sum of `1 / p` over the primes `p ≤ x`
is `log log x + O(1)`, uniformly for natural `x ≥ 2`. Mathlib at this target's pin has
Chebyshev's bounds but no Mertens estimate; this is the one analytic fact outside Mathlib that
the composite-dilation argument for erdos-69 uses (annex 9445873d on `erdos-69`). It is an
ingredient, not the hard step: nothing about `ω` or irrationality is in it. -/
theorem Opn.erdos_69_mertens_reciprocal_primes :
    ∃ C : ℝ, 0 ≤ C ∧ ∀ x : ℕ, 2 ≤ x →
      |∑ p ∈ Nat.primesLE x, (1 : ℝ) / p - Real.log (Real.log (x : ℝ))| ≤ C := by
  sorry
