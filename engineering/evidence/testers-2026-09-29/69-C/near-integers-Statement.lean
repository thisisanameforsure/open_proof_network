import Mathlib

open scoped ArithmeticFunction.omega

/-! A speculative ingredient for erdos-69 (D-29): the rational side of the composite-dilation route,
packaged. Write `D_a(m) = ∑_{k ≥ 0} ω (a (m + k + 1)) / 2^(k+1)` for the tail dilated by `a`. If
`q · ∑ ω(n)/2^n` is the integer `z`, then along any progression `b + Q t` (`t < T`) with every
prime factor of `a` coprime to `Q`, the numbers `q · D_a(b + Q t)` are on average within
`q · ∑_{p ∣ a} (1/p + 1/T)` of an integer. For a rough dilation `a = 1 + P# (1 + j)` the
node `spec-e0b917d1` bounds `∑_{p ∣ a} 1/p` by `5 / log P`, so rationality forces the dilated tails
close to integers on average; the unconditional half of the route (github.com/plby/lean-proofs,
`ErdosProblems/Erdos69`; see the annex on `erdos-69`) shows a signed combination of them is not.
Proof ingredients: `ω (a n) = ω a + ω n - #{p ∣ a : p ∣ n}`, integrality of `q` times each tail,
and at most `T/p + 1` solutions `t < T` of `p ∣ c + Q t` when `p ∤ Q`. -/

theorem Opn.erdos_69_rational_dilated_tails_near_integers :
    ∀ (q : ℕ) (z : ℤ), (q : ℝ) * ∑' n : ℕ, (ω n : ℝ) / 2 ^ n = z →
      ∀ (a Q b T : ℕ), a ≠ 0 → 0 < T → (∀ p ∈ a.primeFactors, Nat.Coprime p Q) →
        (∑ t ∈ Finset.range T,
            |(q : ℝ) * ∑' k : ℕ, (ω (a * (b + Q * t + (k + 1))) : ℝ) / 2 ^ (k + 1)
              - round ((q : ℝ) * ∑' k : ℕ, (ω (a * (b + Q * t + (k + 1))) : ℝ) / 2 ^ (k + 1))|) / T
          ≤ (q : ℝ) * ∑ p ∈ a.primeFactors, ((1 : ℝ) / p + 1 / T) := by
  sorry
