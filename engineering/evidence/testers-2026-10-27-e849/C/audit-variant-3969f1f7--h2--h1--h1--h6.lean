import Mathlib

open Nat

theorem audit_variant_3969f1f7__h2__h1__h1__h6 :
    (∀ (n m : ℕ), (6 : ℕ) ≤ n → (8 : ℕ) ≤ m → n.choose (3 : ℕ) ≠ m.choose (4 : ℕ))
    =
    (∀ n m : ℕ, 6 ≤ n → 8 ≤ m → n.choose 3 ≠ m.choose 4) := rfl
