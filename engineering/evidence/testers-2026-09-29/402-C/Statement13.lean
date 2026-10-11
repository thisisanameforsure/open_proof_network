import Mathlib

/-! Graham's gcd conjecture (Erdős problem 402) for thirteen-element sets. Let M be the largest
element. If some x has gcd(M, x) ≤ M/13 the pair (M, x) works; otherwise each of the other twelve
elements is x = (j/k)·M with 1 ≤ j < k ≤ 12, so v(x) = 27720·x/M (27720 = lcm(1..12)) is one of 45
integers. Those 45 values split into 11 classes in each of which any two distinct values c, d have
13·gcd(c, d) ≤ c or ≤ d. Twelve elements in eleven classes put two in one class, and
gcd(x, y)·27720 = gcd(v(x), v(y))·M carries the bound back to x and y. -/

theorem Opn.erdos_402_card_thirteen :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 13 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  sorry
