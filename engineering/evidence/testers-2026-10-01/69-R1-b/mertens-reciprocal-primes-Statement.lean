import Mathlib

/-! Mertens' second theorem, bounded-error form: `∑_{p ≤ x} 1/p = log log x + O(1)`.
The one fact the composite-dilation route to erdos-69 needs that Mathlib at the pin lacks
(annex 9445873d on `erdos-69`).

The first step (`hM`, the estimate with logarithmic weights `∑_{p ≤ n} (log p)/p = log n + O(1)`)
is adapted from `BoundedGaps/Maynard/PrimeMertens.lean` of github.com/frenzymath/FormalPantheon
(commit ffbb65c21afc8a36ace67720f1b0df1c63d26bd1, Apache-2.0): that file's lemmas are inlined as
`have` steps and its four definitions expanded in place. The rest (discrete Abel summation against
`1/log n`, and `log (b/a)` squeezed between `1 - a/b` and `b/a - 1`) is new. -/
theorem Opn.erdos_69_mertens_reciprocal_primes :
    ∃ C : ℝ, 0 ≤ C ∧ ∀ x : ℕ, 2 ≤ x →
      |∑ p ∈ Nat.primesLE x, (1 : ℝ) / p - Real.log (Real.log (x : ℝ))| ≤ C := by
  sorry
