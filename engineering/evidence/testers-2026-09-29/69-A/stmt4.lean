import Mathlib

open scoped ArithmeticFunction.omega

/-! A speculative ingredient for erdos-69 (D-29): if a binary-weighted series `∑ f(n)/2^n`
of natural numbers is rational, its tails `∑' j, f (n + 1 + j) / 2^(j+1)` are eventually
periodic modulo 1: there are `p > 0` and `N₀` such that any two tails from `n, n' ≥ N₀` with
`n ≡ n' [MOD p]` differ by an integer. Proof: the tail is `2^n x` minus an integer, and `2^n q`
is eventually periodic mod 1 by pigeonhole on `2^n · num mod den`. With `f = ω` this is the
first step of a proof of erdos-69 by contradiction (the tails the nodes under erdos-69--h2-v2
use are exactly these, with `f = ω`); what would remain is to exhibit two tails in one class
that do not differ by an integer, which is the hard part and is not here. The statement is
over any `f` so that its hypotheses are satisfiable (for `f = ω` they are not, the target's
sum being irrational), as step 7 requires. -/

theorem Opn.erdos_69_rational_tails_periodic :
    ∀ (f : ℕ → ℕ) (q : ℚ), Summable (fun n : ℕ => (f n : ℝ) / 2 ^ n) →
      (q : ℝ) = ∑' n : ℕ, (f n : ℝ) / 2 ^ n →
      ∃ p N₀ : ℕ, 0 < p ∧ ∀ n n' : ℕ, N₀ ≤ n → N₀ ≤ n' → n ≡ n' [MOD p] →
        ∃ z : ℤ, ∑' j : ℕ, (f (n + 1 + j) : ℝ) / 2 ^ (j + 1)
          - ∑' j : ℕ, (f (n' + 1 + j) : ℝ) / 2 ^ (j + 1) = z := by
  sorry
