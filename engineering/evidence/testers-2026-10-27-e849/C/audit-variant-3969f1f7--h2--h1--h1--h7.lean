import Mathlib

open Nat

theorem audit_variant_3969f1f7__h2__h1__h1__h7 :
    (∀ (n m : ℕ), (6 : ℕ) ≤ n → (12 : ℕ) ≤ m → n.choose (3 : ℕ) ≠ m.choose (6 : ℕ))
    =
    (∀ n m : ℕ, 6 ≤ n → 12 ≤ m → n.choose 3 ≠ m.choose 6) := rfl
