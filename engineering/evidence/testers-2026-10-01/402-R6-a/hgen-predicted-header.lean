import Mathlib

open Filter

theorem erdos_402__h3_v2__h1__h1__h1__h2 : ∀ (B : Finset ℕ),
    (0 : ℕ) ∉ B →
      B.Nonempty →
        B.gcd id = (1 : ℕ) →
          ¬Nat.Prime B.card →
            (∀ (q : ℕ), Nat.Prime q → B.card ≠ q + (1 : ℕ)) →
              (∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b) →
                (∀ a ∈ B, ∀ (p k : ℕ), Nat.Prime p → p ^ k ∣ a → p ^ k < B.card) →
                  (∃ a ∈ B, ∃ b ∈ B, (↑(a.gcd b) : ℚ) ≤ (↑a : ℚ) / (↑B.card : ℚ)) ∨
                    ∃ (p : ℕ), Nat.Prime p ∧ B.card < p ∧ p < 2 * B.card ∧ 2 * (2 * B.card - p) ≤ B.card + 2 ∧
                    ∀ α : ℕ, α < B.card → p < α + B.card →
                      (∃ q : ℕ, Nat.Prime q ∧ B.card ≤ 3 * q ∧ q ∣ α * (p - α)) ∨
                      (∀ x y : ℕ, x < y → x * y ∣ α → B.card * x ≤ α * y) := by
