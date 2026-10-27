import Mathlib

open Nat

theorem audit_variant_3969f1f7__h3__h2 :
    (∃ (a₂ : ℕ),
  ∀ a ≥ a₂,
    ∀ (n k : ℕ),
      (1 : ℕ) ≤ k ∧ Real.exp (Real.log (↑n : ℝ) ^ (5 / 6 : ℝ)) ≤ (↑k : ℝ) ∧ (2 : ℕ) * k ≤ n ∧ n.choose k = a →
        {n' : ℕ |
              ∃ (k' : ℕ),
                (1 : ℕ) ≤ k' ∧
                  k' < k ∧
                    n < n' ∧
                      (2 : ℕ) * k' ≤ n' ∧
                        n'.choose k' = a ∧
                          |(↑n : ℝ) - (↑n' : ℝ)| + |(↑k : ℝ) - (↑k' : ℝ)| ≤
                            Real.exp (Real.log (Real.log (↑a : ℝ)) ^ (9 / 10 : ℝ))}.ncard ≤
          (1 : ℕ))
    =
    (∃ a₂ : ℕ, ∀ a ≥ a₂, ∀ n k : ℕ,
          (1 ≤ k ∧ Real.exp (Real.log (n : ℝ) ^ (5 / 6 : ℝ)) ≤ (k : ℝ) ∧ 2 * k ≤ n ∧ n.choose k = a) →
          {n' : ℕ | ∃ k' : ℕ, 1 ≤ k' ∧ k' < k ∧ n < n' ∧ 2 * k' ≤ n' ∧ n'.choose k' = a ∧
              |(n : ℝ) - n'| + |(k : ℝ) - k'| ≤
                Real.exp (Real.log (Real.log (a : ℝ)) ^ (9 / 10 : ℝ))}.ncard ≤ 1) := rfl
