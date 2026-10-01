import Mathlib

/-! Graham's gcd conjecture (Erdős problem 402) restricted to sets of exactly seventeen elements.
Route: let M be the largest element. Either some x has 17 · gcd(M, x) ≤ M, and the pair (M, x)
works, or every other x has M < 17 · gcd(M, x), so M = k·g and x = j·g with g = gcd(M, x) and
1 ≤ j < k ≤ 16; then 720720 · x / M (720720 = lcm(1..16)) takes one of 79 values. A computer
search finds a split of those 79 values into 15 classes in each of which two distinct values
c, d satisfy 17 · gcd(c, d) ≤ max(c, d); sixteen elements in fifteen classes force two into one
class, and gcd(x, y) · 720720 = gcd(c, d) · M carries the bound back to x and y. -/

theorem Opn.erdos_402_card_seventeen :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 17 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  sorry
