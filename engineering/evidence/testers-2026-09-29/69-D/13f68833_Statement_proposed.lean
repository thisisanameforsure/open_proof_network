import Mathlib
import Nodes.«spec-13f68833».Context

open scoped ArithmeticFunction.omega

/-! A speculative ingredient for erdos-69 (D-29): a linear bound on `ω` bounds the tail.
If `ω (n + 1 + k) ≤ C (k + 1)` for every `k`, then the tail
`∑' j, ω (n + 1 + j) / 2^(j+1)` (the same expression the nodes under erdos-69--h2-v2 use) is at
most `2 C`, because `∑_{j ≥ 0} (j + 1) / 2^(j+1) = 2`. The literature route
(Tao–Teräväinen, arXiv:2512.01739, abstract) gives infinitely many `n` with `ω (n + k) ≪ k`
for all `k ≥ 1`; with this lemma the tails at those `n` are bounded by a constant. That is a
bridge, not the hard step. -/

theorem Opn.erdos_69_tail_le_of_linear_bound :
    ∀ (n : ℕ) (C : ℝ), (∀ k : ℕ, (ω (n + 1 + k) : ℝ) ≤ C * ((k : ℝ) + 1)) →
      ∑' j : ℕ, (ω (n + 1 + j) : ℝ) / 2 ^ (j + 1) ≤ 2 * C := by
  sorry
