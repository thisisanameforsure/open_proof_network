import Mathlib

open scoped ArithmeticFunction.omega

theorem witness : ∃ (n : ℕ) (C : ℝ), ∀ k : ℕ, (ω (n + 1 + k) : ℝ) ≤ C * ((k : ℝ) + 1) := by
  refine ⟨0, 2, fun k => ?_⟩
  have hsub : (0 + 1 + k).primeFactors ⊆ Finset.range (0 + 1 + k + 1) := by
    intro p hp
    have hp' := Nat.mem_primeFactors.1 hp
    exact Finset.mem_range.2 (Nat.lt_succ_of_le (Nat.le_of_dvd (by omega) hp'.2.1))
  have hcard := Finset.card_le_card hsub
  rw [Finset.card_range] at hcard
  have hω : ω (0 + 1 + k) = (0 + 1 + k).primeFactors.card := by
    rw [ArithmeticFunction.cardDistinctFactors_apply, Nat.primeFactors, List.card_toFinset]
  have h1 : ω (0 + 1 + k) ≤ 2 * (k + 1) := by omega
  have h2 : ((ω (0 + 1 + k) : ℕ) : ℝ) ≤ ((2 * (k + 1) : ℕ) : ℝ) := by exact_mod_cast h1
  push_cast at h2
  linarith
