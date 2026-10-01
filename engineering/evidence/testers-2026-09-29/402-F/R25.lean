import Mathlib

theorem relation :
    (∀ (A : Finset ℕ), 0 ∉ A → A.Nonempty → ∃ᵉ (a ∈ A) (b ∈ A), a.gcd b ≤ (a / A.card : ℚ)) →
    (∀ (A : Finset ℕ), 0 ∉ A → A.card = 25 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ)) := by
  intro h A h0 hc
  exact h A h0 (Finset.card_pos.mp (by omega))
