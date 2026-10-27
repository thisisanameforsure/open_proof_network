import Mathlib

open Nat

/-- Audit: the gate-written hole `variant-3969f1f7--h2` (left) is the partial's `have h_middle` (right). -/
theorem audit_h2 :
    (∃ (K : ℕ) (B : ℕ),
      ∀ (a : ℕ),
        {n : ℕ |
              ∃ (k : ℕ),
                K < k ∧ (↑k : ℝ) < Real.exp (Real.log (↑n : ℝ) ^ (5 / 6 : ℝ)) ∧ (2 : ℕ) * k ≤ n ∧ n.choose k = a}.ncard ≤
          B)
    =
    (∃ K B : ℕ, ∀ a : ℕ, {n : ℕ | ∃ k : ℕ, K < k ∧
          (k : ℝ) < Real.exp (Real.log n ^ ((5 : ℝ) / 6)) ∧ 2 * k ≤ n ∧ choose n k = a}.ncard ≤ B) := rfl

/-- Audit: the gate-written hole `variant-3969f1f7--h3` (left) is the partial's `have h_interior` (right). -/
theorem audit_h3 :
    (∃ (a₀ : ℕ),
      ∀ a ≥ a₀,
        {n : ℕ |
              ∃ (k : ℕ),
                (1 : ℕ) ≤ k ∧
                  Real.exp (Real.log (↑n : ℝ) ^ (5 / 6 : ℝ)) ≤ (↑k : ℝ) ∧ (2 : ℕ) * k ≤ n ∧ n.choose k = a}.ncard ≤
          (2 : ℕ))
    =
    (∃ a₀ : ℕ, ∀ a ≥ a₀, {n : ℕ | ∃ k : ℕ, 1 ≤ k ∧
          Real.exp (Real.log n ^ ((5 : ℝ) / 6)) ≤ (k : ℝ) ∧ 2 * k ≤ n ∧ choose n k = a}.ncard ≤ 2) := rfl

-- The exponent is a real 5/6, not the natural-number quotient 0 cast to ℝ.
theorem audit_exponent : (5 / 6 : ℝ) = (5 : ℝ) / (6 : ℝ) := rfl
theorem audit_exponent_pos : (0 : ℝ) < (5 / 6 : ℝ) := by norm_num

set_option pp.numericTypes true in
set_option pp.coercions.types true in
#check (∃ (K : ℕ) (B : ℕ), ∀ (a : ℕ), {n : ℕ | ∃ (k : ℕ), K < k ∧ (↑k : ℝ) < Real.exp (Real.log (↑n : ℝ) ^ (5 / 6 : ℝ)) ∧ (2 : ℕ) * k ≤ n ∧ n.choose k = a}.ncard ≤ B)
