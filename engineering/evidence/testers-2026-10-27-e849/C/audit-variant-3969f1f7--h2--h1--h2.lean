import Mathlib

open Nat

theorem audit_variant_3969f1f7__h2__h1__h2 :
    (∀ (n k m l : ℕ),
  (2 : ℕ) ≤ k →
    (2 : ℕ) * k ≤ n →
      (2 : ℕ) ≤ l →
        (2 : ℕ) * l ≤ m →
          k < l →
            n.choose k = m.choose l →
              m + (1 : ℕ) = n →
                l = k + (1 : ℕ) →
                  ∃ (i : ℕ),
                    (1 : ℕ) ≤ i ∧
                      n = Nat.fib ((2 : ℕ) * i + (2 : ℕ)) * Nat.fib ((2 : ℕ) * i + (3 : ℕ)) ∧
                        k = Nat.fib ((2 : ℕ) * i) * Nat.fib ((2 : ℕ) * i + (3 : ℕ)) ∧ m + (1 : ℕ) = n ∧ l = k + (1 : ℕ))
    =
    (∀ n k m l : ℕ, 2 ≤ k → 2 * k ≤ n → 2 ≤ l → 2 * l ≤ m → k < l → choose n k = choose m l →
          m + 1 = n → l = k + 1 →
          ∃ i : ℕ, 1 ≤ i ∧ n = fib (2 * i + 2) * fib (2 * i + 3) ∧ k = fib (2 * i) * fib (2 * i + 3) ∧
            m + 1 = n ∧ l = k + 1) := rfl
