import Mathlib

open Nat

theorem audit_variant_3969f1f7__h3__h1__h1 :
    (∃ (C : ℝ),
  (0 : ℝ) ≤ C ∧
    ∃ (a₁ : ℕ),
      ∀ a ≥ a₁,
        ∀ (n k n' k' : ℕ),
          (1 : ℕ) ≤ k ∧ (2 : ℕ) * k ≤ n ∧ n.choose k = a →
            (1 : ℕ) ≤ k' ∧ (2 : ℕ) * k' ≤ n' ∧ n'.choose k' = a →
              |(↑k : ℝ) - (↑k' : ℝ)| ≤ C * Real.exp (Real.log ((↑n : ℝ) + (↑n' : ℝ)) ^ (43 / 60 : ℝ)) ∧
                (Real.exp (Real.log ((↑n : ℝ) + (↑n' : ℝ)) ^ (43 / 60 : ℝ)) ≤ (↑k : ℝ) →
                  Real.exp (Real.log ((↑n : ℝ) + (↑n' : ℝ)) ^ (43 / 60 : ℝ)) ≤ (↑k' : ℝ) →
                    |(↑n : ℝ) - (↑n' : ℝ)| ≤ C * Real.exp (Real.log ((↑n : ℝ) + (↑n' : ℝ)) ^ (43 / 60 : ℝ))))
    =
    (∃ C : ℝ, 0 ≤ C ∧ ∃ a₁ : ℕ, ∀ a ≥ a₁, ∀ n k n' k' : ℕ,
          (1 ≤ k ∧ 2 * k ≤ n ∧ n.choose k = a) → (1 ≤ k' ∧ 2 * k' ≤ n' ∧ n'.choose k' = a) →
          |(k : ℝ) - k'| ≤ C * Real.exp (Real.log ((n : ℝ) + n') ^ (43 / 60 : ℝ)) ∧
          (Real.exp (Real.log ((n : ℝ) + n') ^ (43 / 60 : ℝ)) ≤ k →
            Real.exp (Real.log ((n : ℝ) + n') ^ (43 / 60 : ℝ)) ≤ k' →
            |(n : ℝ) - n'| ≤ C * Real.exp (Real.log ((n : ℝ) + n') ^ (43 / 60 : ℝ)))) := rfl
