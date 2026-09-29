import Mathlib

/-! Graham's gcd conjecture (Erdős problem 402) for twenty-five-element sets, closed by the
reduction `Opn.erdos_402_card_of_colouring` (declared dependency): with L = lcm(1..24),
the 179 values L·j/k (1 ≤ j < k < 25) split into 23 classes in which any two distinct values a, b
have 25·gcd(a, b) ≤ max(a, b), so pigeonhole on the 24 elements below the maximum finishes. -/

theorem Opn.erdos_402_card_twenty_five :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 25 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  sorry
