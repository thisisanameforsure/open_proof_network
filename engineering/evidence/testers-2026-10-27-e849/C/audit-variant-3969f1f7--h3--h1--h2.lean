import Mathlib

open Nat

theorem audit_variant_3969f1f7__h3__h1__h2 :
    (∀ (a n k : ℕ),
  (1 : ℕ) ≤ k →
    (2 : ℕ) * k ≤ n →
      n.choose k = a →
        Real.log (↑a : ℝ) ≤ (↑k : ℝ) * Real.log (↑n : ℝ) ∧
          ((3 : ℕ) ≤ k → (↑k : ℝ) ≤ (2 : ℝ) * Real.log (↑a : ℝ)) ∧
            (Real.exp (Real.log (↑n : ℝ) ^ (5 / 6 : ℝ)) ≤ (↑k : ℝ) →
              (3 : ℕ) ≤ k ∧ Real.log (↑n : ℝ) ≤ Real.log (↑k : ℝ) ^ (6 / 5 : ℝ)))
    =
    (∀ a n k : ℕ, 1 ≤ k → 2 * k ≤ n → n.choose k = a →
          Real.log a ≤ k * Real.log n ∧ (3 ≤ k → (k : ℝ) ≤ 2 * Real.log a) ∧
          (Real.exp (Real.log (n : ℝ) ^ (5 / 6 : ℝ)) ≤ (k : ℝ) →
            3 ≤ k ∧ Real.log n ≤ Real.log k ^ (6 / 5 : ℝ))) := rfl
