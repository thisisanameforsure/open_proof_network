import Mathlib

/-! Singmaster's conjecture (1971) in the row form of Erdős 849: there is an absolute bound
`B` on the number of rows `n` of Pascal's half triangle `1 ≤ k ≤ n/2` holding any given value
`a`. Proved, it refutes the affirmative root `Opn.erdos_849` (take `t = B + 1`). -/

open Nat

theorem Opn.erdos_849_singmaster_bounded :
    ∃ B : ℕ, ∀ a : ℕ,
      {n : ℕ | ∃ k ≥ 1, 2 * k ≤ n ∧ choose n k = a}.ncard ≤ B := by
  sorry
