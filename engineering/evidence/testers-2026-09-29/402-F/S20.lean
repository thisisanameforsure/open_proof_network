import Mathlib

/-! Graham's gcd conjecture (Erdős problem 402) for twenty-element sets, stated to be closed by
the reduction `Opn.erdos_402_card_of_colouring` (declared dependency): with L = lcm(1..19),
the 119 values L·j/k (1 ≤ j < k < 20) split into 18 classes in which any two distinct values a, b
have 20·gcd(a, b) ≤ max(a, b), so pigeonhole on the 19 elements below the maximum finishes. -/

theorem Opn.erdos_402_card_twenty :
    ∀ (A : Finset ℕ), 0 ∉ A → A.card = 20 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ) := by
  sorry
