import Mathlib

open Nat

theorem audit_variant_3969f1f7__h2__h1__h4__h2__h2 :
    (∀ (n k : ℕ), (2 : ℕ) ≤ k → (2 : ℕ) * (k + (1 : ℕ)) + (2 : ℕ) ≤ n → n.choose k ≠ (n - (2 : ℕ)).choose (k + (1 : ℕ)))
    =
    (∀ n k : ℕ, 2 ≤ k → 2 * (k + 1) + 2 ≤ n → choose n k ≠ choose (n - 2) (k + 1)) := rfl
