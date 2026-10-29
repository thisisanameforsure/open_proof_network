import Mathlib

open Nat

theorem audit_variant_3969f1f7__h2__h1__h1__h9 :
    (∀ (n m : ℕ), (8 : ℕ) ≤ n → (16 : ℕ) ≤ m → n.choose (4 : ℕ) ≠ m.choose (8 : ℕ))
    =
    (∀ n m : ℕ, 8 ≤ n → 16 ≤ m → n.choose 4 ≠ m.choose 8) := rfl
