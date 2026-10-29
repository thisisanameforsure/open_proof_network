import Mathlib

open Nat

theorem audit_variant_3969f1f7__h3__h1__h3 :
    (∀ (C : ℝ),
  ∃ (X₀ : ℝ),
    ∀ X ≥ X₀,
      ((1 : ℝ) + (X + (1 : ℝ)) ^ (6 / 5 : ℝ)) ^ (43 / 60 : ℝ) ≤ X - (6 / 5 : ℝ) * Real.log (X + (1 : ℝ)) ∧
        C * Real.exp (((1 : ℝ) + (X + (1 : ℝ)) ^ (6 / 5 : ℝ)) ^ (43 / 60 : ℝ)) ≤ Real.exp (X ^ (9 / 10 : ℝ)))
    =
    (∀ C : ℝ, ∃ X₀ : ℝ, ∀ X ≥ X₀,
          (1 + (X + 1) ^ (6 / 5 : ℝ)) ^ (43 / 60 : ℝ) ≤ X - 6 / 5 * Real.log (X + 1) ∧
          C * Real.exp ((1 + (X + 1) ^ (6 / 5 : ℝ)) ^ (43 / 60 : ℝ)) ≤ Real.exp (X ^ (9 / 10 : ℝ))) := rfl
