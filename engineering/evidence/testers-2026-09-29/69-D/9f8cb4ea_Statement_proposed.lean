import Mathlib
import Nodes.«spec-9f8cb4ea».Context

open scoped ArithmeticFunction.omega

/-! A speculative ingredient for erdos-69 (D-29): the composite-dilation identity for the tails,
in closed form. For `a ≠ 0` and every `m`,
`∑' k, ω (a (m+k+1)) / 2^(k+1) = ∑' k, ω (m+k+1) / 2^(k+1) + ω a
  − ∑_{p ∣ a prime} 2^(m mod p) / (2^p − 1)`.
Pointwise it is `ω (a x) + #{p ∣ a : p ∣ x} = ω a + ω x` (inclusion–exclusion on prime
factors), summed against `1/2^(k+1)`; the multiples of `p` among `m+1, m+2, …` carry binary
weight exactly `2^(m mod p) / (2^p − 1)`. So a dilated tail differs from the tail itself by a
rational number with denominator dividing `∏_{p ∣ a} (2^p − 1)`: if `∑ ω(n)/2^n` were rational,
a fixed integer multiple of every dilated tail would be an integer as well. 69-C reports
(annex on erdos-69, graph PR #256) that an external formal proof of Erdős 69 rests on a
dilation identity of this kind. The identity alone proves nothing about irrationality. -/

theorem Opn.erdos_69_dilated_tail_closed :
    ∀ (a m : ℕ), a ≠ 0 →
      ∑' k : ℕ, (ω (a * (m + (k + 1))) : ℝ) / 2 ^ (k + 1)
        = ∑' k : ℕ, (ω (m + (k + 1)) : ℝ) / 2 ^ (k + 1) + (ω a : ℝ)
          - ∑ p ∈ a.primeFactors, (2 : ℝ) ^ (m % p) / (2 ^ p - 1) := by
  sorry
