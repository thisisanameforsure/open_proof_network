import Mathlib
import Nodes.«spec-f1cadf9f».Context

open scoped ArithmeticFunction.omega

/-! A speculative ingredient for erdos-69 (D-29): the composite-dilation identity for the tails.
For `a ≠ 0`, dilating a tail by `a` changes it by `ω a` minus, for each prime `p ∣ a`, the
binary-weighted density of the terms `m + k + 1` that `p` divides:
`∑' k, ω (a (m+k+1)) / 2^(k+1) = ∑' k, ω (m+k+1) / 2^(k+1) + ω a
  - ∑_{p ∣ a} ∑' k, [p ∣ m+k+1] / 2^(k+1)`.
Pointwise it is `ω (a x) + #{p ∣ a : p ∣ x} = ω a + ω x` (inclusion–exclusion on prime
factors), summed against `1/2^(k+1)`. 69-C reports (annex on erdos-69, graph PR #256) that an
external formal proof of Erdős 69 rests on this identity; with rationality making a fixed
multiple of every tail an integer, it constrains dilated tails too. The identity alone proves
nothing about irrationality. -/

theorem Opn.erdos_69_dilated_tail :
    ∀ (a m : ℕ), a ≠ 0 →
      ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
        = ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ)
          - ∑ p ∈ a.primeFactors,
              ∑' k : ℕ, (if p ∣ m + (k + 1) then (1 : ℝ) else 0) / 2 ^ (k + 1) := by
  sorry
