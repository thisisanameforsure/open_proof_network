import Mathlib

open Nat

theorem audit_variant_3969f1f7__h2__h1__h1__h4 :
    (∀ (n m : ℕ), (4 : ℕ) ≤ n → (12 : ℕ) ≤ m → n.choose (2 : ℕ) = m.choose (6 : ℕ) → n = (78 : ℕ) ∧ m = (14 : ℕ))
    =
    (∀ n m : ℕ, 4 ≤ n → 12 ≤ m → n.choose 2 = m.choose 6 → (n = 78 ∧ m = 14)) := rfl
