import Mathlib

open Nat

theorem audit_variant_3969f1f7__h2__h1__h1__h5 :
    (∀ (n m : ℕ), (4 : ℕ) ≤ n → (16 : ℕ) ≤ m → n.choose (2 : ℕ) = m.choose (8 : ℕ) → n = (221 : ℕ) ∧ m = (17 : ℕ))
    =
    (∀ n m : ℕ, 4 ≤ n → 16 ≤ m → n.choose 2 = m.choose 8 → (n = 221 ∧ m = 17)) := rfl
