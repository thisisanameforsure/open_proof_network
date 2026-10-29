import Mathlib

open Nat

theorem audit_variant_3969f1f7__h2__h1__h1__h2 :
    (∀ (n m : ℕ), (4 : ℕ) ≤ n → (8 : ℕ) ≤ m → n.choose (2 : ℕ) = m.choose (4 : ℕ) → n = (21 : ℕ) ∧ m = (10 : ℕ))
    =
    (∀ n m : ℕ, 4 ≤ n → 8 ≤ m → n.choose 2 = m.choose 4 → (n = 21 ∧ m = 10)) := rfl
