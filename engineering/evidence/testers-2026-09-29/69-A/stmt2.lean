import Mathlib

open scoped ArithmeticFunction.omega

/-! A speculative ingredient for erdos-69 (D-29): prescribed lower bounds for `ω` on a window of
consecutive integers. For every length `k` and every choice of lower bounds `c 0, …, c (k-1)`
there is `N` with `c j ≤ ω (N + 1 + j)` for each `j < k`: give each slot its own set of distinct
primes and solve the congruences by the Chinese remainder theorem. Rationality of
`∑ ω(n)/2^n` would make every tail `∑_{j ≥ 0} ω(N+1+j)/2^(j+1)` lie in a fixed lattice
`(1/b)ℤ`, and arguments against that (the literature route is Tao–Teräväinen, arXiv:2512.01739)
need windows whose `ω` values are controlled. This lemma is only the elementary, lower-bound
half of that control; the upper bounds, the hard part, are not here. -/

theorem Opn.erdos_69_omega_window :
    ∀ (k : ℕ) (c : ℕ → ℕ), ∃ N : ℕ, ∀ j < k, c j ≤ ω (N + 1 + j) := by
  sorry
