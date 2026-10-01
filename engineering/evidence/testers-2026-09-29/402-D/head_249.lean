import Mathlib
import Nodes.«variant-b0d58c5d».Context

/-! Graham's gcd conjecture (Erdős problem 402) restricted to sets of exactly fourteen positive
integers. Let M be the largest element. Either some x has gcd(M, x) ≤ M/14, or each other
element is (j/k)·M with 1 ≤ j < k ≤ 13, and multiplying by L = lcm(1..13) = 360360 and dividing
by M sends it to L·j/k, one of 57 fixed integers. Those 57 fall into 12 classes such that two
distinct members c, d of one class always have 14·gcd(c, d) ≤ c or 14·gcd(c, d) ≤ d. Thirteen
non-maximal elements in 12 classes put two, x and y, in one class, and gcd(x, y)·L = gcd(c, d)·M
carries the bound back to x and y. -/

theorem Opn.erdos_402_card_fourteen :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 14 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  sorry
