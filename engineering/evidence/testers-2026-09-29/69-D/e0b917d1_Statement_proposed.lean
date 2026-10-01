import Mathlib
import Nodes.«spec-e0b917d1».Context

/-! A speculative ingredient for erdos-69 (D-29): the correction mass of a rough dilation.
In the composite-dilation route to the irrationality of `∑ ω(n)/2^n` (see the annex on
`erdos-69` describing github.com/plby/lean-proofs, `ErdosProblems/Erdos69/RoughSizeBounds.lean`,
`roughDilation_reciprocal_mass_le`), dilating the sequence by `a = 1 + P# · (1 + j)` changes
the binary tail by a correction whose mean is controlled by `∑_{p ∣ a} 1/p`. Every prime factor of
`a` exceeds `P`, and `a ≤ 16^P`, so that sum is at most `5 / log P`. -/

theorem Opn.erdos_69_rough_dilation_reciprocal :
    ∀ P j : ℕ, 2 ≤ P → j ≤ P →
      ∑ p ∈ (1 + primorial P * (1 + j)).primeFactors, (1 : ℝ) / p ≤ 5 / Real.log P := by
  sorry
