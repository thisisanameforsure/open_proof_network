import Mathlib

open scoped ArithmeticFunction.omega
open Filter Topology

theorem chk_anc :
    Irrational <| ∑' n, ω (n + 2) / 2 ^ (n + 2) := by
  sorry

theorem chk_hole :
    (∑' n : ℕ, (ω n : ℝ) / 2 ^ n = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) →
    ∀ b : ℕ, 0 < b → ∃ N : ℕ, ∀ z : ℤ,
      (b : ℝ) * ∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1) ≠ (z : ℝ) := by
  sorry



/-- erdos-69--h2-v2--h1-v2 is no easier than the root erdos-69: the root implies it with
N = 0, because the rescaled tail at N = 0 is the root's series (D-12, D-16 v3.21). -/
theorem erdos_69_h2_v2_h1_v2_circular :
    (Irrational <| ∑' n, ω (n + 2) / 2 ^ (n + 2)) →
    ((∑' n : ℕ, (ω n : ℝ) / 2 ^ n = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) →
    ∀ b : ℕ, 0 < b → ∃ N : ℕ, ∀ z : ℤ,
      (b : ℝ) * ∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1) ≠ (z : ℝ)) := by
  intro hroot _hL b hb
  refine ⟨0, fun z => ?_⟩
  have hsum2 : Summable (fun n : ℕ => (ω (n + 2) : ℝ) / 2 ^ (n + 2)) := by
    by_contra hns
    have h := hroot
    rw [tsum_eq_zero_of_not_summable hns] at h
    exact h ⟨0, by simp⟩
  have hsum : Summable (fun j : ℕ => (ω (0 + 1 + j) : ℝ) / 2 ^ (j + 1)) := by
    rw [← summable_nat_add_iff 1]
    refine hsum2.congr (fun j => ?_)
    rw [show 0 + 1 + (j + 1) = j + 2 by omega, show j + 1 + 1 = j + 2 by omega]
  have hS : ∑' j : ℕ, (ω (0 + 1 + j) : ℝ) / 2 ^ (j + 1) = ∑' n : ℕ, (ω (n + 2) : ℝ) / 2 ^ (n + 2) := by
    rw [hsum.tsum_eq_zero_add]
    rw [show 0 + 1 + 0 = 1 from rfl, ArithmeticFunction.cardDistinctFactors_one, Nat.cast_zero, zero_div,
      zero_add]
    refine tsum_congr (fun j => ?_)
    rw [show 0 + 1 + (j + 1) = j + 2 by omega, show j + 1 + 1 = j + 2 by omega]
  rw [hS]
  exact (hroot.natCast_mul (Nat.pos_iff_ne_zero.mp hb)).ne_int z

example : (type_of% @chk_anc → type_of% @chk_hole) = type_of% @erdos_69_h2_v2_h1_v2_circular := rfl
