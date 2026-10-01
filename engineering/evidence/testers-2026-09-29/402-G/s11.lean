import Mathlib

/-! Graham's gcd conjecture (Erdős problem 402) for eleven-element sets. With M the largest
element, if gcd(M, x) > M/11 for every x then every other x is (j/k)M with j < k ≤ 10, so
L·x/M (L = lcm(1..10) = 2520) lies in a fixed set S of 31 values. S splits into 9 classes in
each of which any two distinct values c, d have 11·gcd(c, d) ≤ c or ≤ d; by pigeonhole two of
the 10 other elements share a class, and gcd(x, y)·L = gcd(c, d)·M transfers the bound. -/

theorem Opn.erdos_402_card_eleven :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 11 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  sorry
