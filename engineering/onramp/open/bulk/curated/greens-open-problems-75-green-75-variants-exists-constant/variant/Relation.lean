import Mathlib
import Defs.Local

open scoped Finset
open Green75

/-- `partial`: the root (`green_75`, the constant 100) implies this variant, with C = 100. -/
theorem relation :
    (∀ X : Finset (ℝ × ℝ), 2 ≤ #X → ∃ p ∈ X, ∃ q ∈ X, p ≠ q ∧ imbalance X p q ≤ 100) →
    ∃ C : ℕ, ∀ X : Finset (ℝ × ℝ), 2 ≤ #X →
      ∃ p ∈ X, ∃ q ∈ X, p ≠ q ∧ imbalance X p q ≤ C := by
  intro h
  refine ⟨100, fun X hX => ?_⟩
  obtain ⟨p, hp, q, hq, hne, hle⟩ := h X hX
  exact ⟨p, hp, q, hq, hne, by exact_mod_cast hle⟩
