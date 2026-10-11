import Mathlib

/-! Graham's gcd conjecture (Erdős problem 402) restricted to sets of exactly fifteen elements.
Route: let M be the largest element. Either some x has 15 · gcd(M, x) ≤ M, and the pair (M, x)
works, or every other x has M < 15 · gcd(M, x), so M = k·g and x = j·g with g = gcd(M, x) and
1 ≤ j < k ≤ 14; then 360360 · x / M (360360 = lcm(1..14)) takes one of 63 values. A computer
search finds a split of those 63 values into 13 classes in each of which two distinct values
c, d satisfy 15 · gcd(c, d) ≤ max(c, d); fourteen elements in thirteen classes force two into one
class, and gcd(x, y) · 360360 = gcd(c, d) · M carries the bound back to x and y. -/

theorem Opn.erdos_402_card_fifteen :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 15 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  sorry
