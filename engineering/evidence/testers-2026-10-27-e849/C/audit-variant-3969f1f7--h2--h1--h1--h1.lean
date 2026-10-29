import Mathlib

open Nat

theorem audit_variant_3969f1f7__h2__h1__h1__h1 :
    (∀ (n m : ℕ),
  (4 : ℕ) ≤ n →
    (6 : ℕ) ≤ m →
      n.choose (2 : ℕ) = m.choose (3 : ℕ) →
        n = (16 : ℕ) ∧ m = (10 : ℕ) ∨ n = (56 : ℕ) ∧ m = (22 : ℕ) ∨ n = (120 : ℕ) ∧ m = (36 : ℕ))
    =
    (∀ n m : ℕ, 4 ≤ n → 6 ≤ m → n.choose 2 = m.choose 3 → (n = 16 ∧ m = 10) ∨ (n = 56 ∧ m = 22) ∨ (n = 120 ∧ m = 36)) := rfl
