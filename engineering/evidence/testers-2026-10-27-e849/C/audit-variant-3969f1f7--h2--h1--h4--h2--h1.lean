import Mathlib

open Nat

theorem audit_variant_3969f1f7__h2__h1__h4__h2__h1 :
    (∀ (n k : ℕ), (2 : ℕ) ≤ k → (2 : ℕ) * (k + (2 : ℕ)) + (1 : ℕ) ≤ n → n.choose k ≠ (n - (1 : ℕ)).choose (k + (2 : ℕ)))
    =
    (∀ n k : ℕ, 2 ≤ k → 2 * (k + 2) + 1 ≤ n → choose n k ≠ choose (n - 1) (k + 2)) := rfl
