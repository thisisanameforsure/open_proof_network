import Mathlib

open Nat

theorem audit_variant_3969f1f7__h2__h1__h1__h3 :
    (∀ (n m : ℕ),
  (4 : ℕ) ≤ n →
    (10 : ℕ) ≤ m → n.choose (2 : ℕ) = m.choose (5 : ℕ) → n = (78 : ℕ) ∧ m = (15 : ℕ) ∨ n = (153 : ℕ) ∧ m = (19 : ℕ))
    =
    (∀ n m : ℕ, 4 ≤ n → 10 ≤ m → n.choose 2 = m.choose 5 → (n = 78 ∧ m = 15) ∨ (n = 153 ∧ m = 19)) := rfl
