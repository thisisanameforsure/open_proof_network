import Mathlib

open scoped ArithmeticFunction.omega

/-! A speculative ingredient for erdos-69 (D-29): the rational side of the composite-dilation
route. If `q · ∑ ω(n)/2^n` is the integer `z`, then for every dilation `a ≠ 0` and every `m`,
`q` times (the dilated tail `∑_{k ≥ 0} ω(a (m + k + 1))/2^(k+1)` plus its correction
`∑_{p ∣ a} ∑_{k ≥ 0} [p ∣ m + k + 1]/2^(k+1)`) is an integer. No primality of `a` is needed,
which is what lets rough composite dilations replace prime-tuple inputs (github.com/plby/lean-proofs,
`ErdosProblems/Erdos69/CompositeTails.lean`, `integer_mul_corrected_dilatedTail`; see the annex on
`erdos-69`). -/

theorem Opn.erdos_69_rational_dilated_tail_integral :
    ∀ (q : ℕ) (z : ℤ), (q : ℝ) * ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = z →
      ∀ a m : ℕ, a ≠ 0 → ∃ t : ℤ,
        (q : ℝ) * (∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
          + ∑ p ∈ a.primeFactors,
              ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1)) = t := by
  sorry
