import Mathlib

open Nat

theorem audit_variant_3969f1f7__h2__h1__h4__h2__h3 :
    (∀ (n k m l : ℕ),
  (2 : ℕ) ≤ k →
    (2 : ℕ) * k ≤ n →
      (2 : ℕ) ≤ l →
        (2 : ℕ) * l ≤ m →
          k < l →
            n.choose k = m.choose l →
              (k = (2 : ℕ) ∧ l = (3 : ℕ) ∨
                  k = (2 : ℕ) ∧ l = (4 : ℕ) ∨
                    k = (2 : ℕ) ∧ l = (5 : ℕ) ∨
                      k = (2 : ℕ) ∧ l = (6 : ℕ) ∨
                        k = (2 : ℕ) ∧ l = (8 : ℕ) ∨
                          k = (3 : ℕ) ∧ l = (4 : ℕ) ∨
                            k = (3 : ℕ) ∧ l = (6 : ℕ) ∨ k = (4 : ℕ) ∧ l = (6 : ℕ) ∨ k = (4 : ℕ) ∧ l = (8 : ℕ)) ∨
                m + (1 : ℕ) = n ∧ l = k + (1 : ℕ) ∨
                  n ≤ (1000000 : ℕ) ∨
                    n.choose k ≤ (10 : ℕ) ^ (60 : ℕ) ∨
                      m + (1 : ℕ) = n ∧ l = k + (2 : ℕ) ∨ m + (2 : ℕ) = n ∧ l = k + (1 : ℕ))
    =
    (∀ n k m l : ℕ, 2 ≤ k → 2 * k ≤ n → 2 ≤ l → 2 * l ≤ m → k < l → choose n k = choose m l →
          ((k = 2 ∧ l = 3) ∨ (k = 2 ∧ l = 4) ∨ (k = 2 ∧ l = 5) ∨ (k = 2 ∧ l = 6) ∨ (k = 2 ∧ l = 8) ∨
           (k = 3 ∧ l = 4) ∨ (k = 3 ∧ l = 6) ∨ (k = 4 ∧ l = 6) ∨ (k = 4 ∧ l = 8)) ∨
          (m + 1 = n ∧ l = k + 1) ∨ n ≤ 1000000 ∨ choose n k ≤ 10 ^ 60 ∨
          (m + 1 = n ∧ l = k + 2) ∨ (m + 2 = n ∧ l = k + 1)) := rfl
