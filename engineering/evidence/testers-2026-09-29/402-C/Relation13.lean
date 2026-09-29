import Mathlib

theorem relation :
    (∀ (A : Finset ℕ), 0 ∉ A → A.Nonempty → ∃ᵉ (a ∈ A) (b ∈ A), a.gcd b ≤ (a / A.card : ℚ)) →
    (∀ (A : Finset ℕ), 0 ∉ A → A.card = 13 → ∃ a ∈ A, ∃ b ∈ A, a.gcd b ≤ (a / A.card : ℚ)) :=
  fun h A hA hn => h A hA (Finset.card_pos.mp (by omega))
