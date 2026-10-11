import Mathlib

open scoped ArithmeticFunction.omega

/-- E1: a linear bound on ω along n+1, n+2, … bounds the tail by 2C. -/
theorem erdos69_tail_le_of_linear_bound (n : ℕ) (C : ℝ)
    (h : ∀ k : ℕ, (ω (n + 1 + k) : ℝ) ≤ C * ((k : ℝ) + 1)) :
    ∑' j : ℕ, (ω (n + 1 + j) : ℝ) / 2 ^ (j + 1) ≤ 2 * C := by
  sorry

/-- E2: if the series is rational, the tails are congruent mod 1 along a progression. -/
theorem erdos69_tails_congruent_of_rational (q : ℚ)
    (hq : (q : ℝ) = ∑' n : ℕ, (ω n : ℝ) / 2 ^ n) :
    ∃ p N₀ : ℕ, 0 < p ∧ ∀ n n' : ℕ, N₀ ≤ n → N₀ ≤ n' → n ≡ n' [MOD p] →
      ∃ z : ℤ, ∑' j : ℕ, (ω (n + 1 + j) : ℝ) / 2 ^ (j + 1)
        - ∑' j : ℕ, (ω (n' + 1 + j) : ℝ) / 2 ^ (j + 1) = z := by
  sorry

/-- E3: every tail from n ≥ 1 is at least 1. -/
theorem erdos69_one_le_tail (n : ℕ) (hn : 1 ≤ n) :
    1 ≤ ∑' j : ℕ, (ω (n + 1 + j) : ℝ) / 2 ^ (j + 1) := by
  sorry

/-- ES (Tao–Teräväinen 2025, the Erdős–Straus conjecture): infinitely many n with
ω(n+k) ≤ C·k for every k ≥ 1, for one absolute C. -/
theorem erdos69_erdos_straus :
    ∃ C : ℕ, ∀ N₀ : ℕ, ∃ n : ℕ, N₀ ≤ n ∧ ∀ k : ℕ, ω (n + 1 + k) ≤ C * (k + 1) := by
  sorry
