import Mathlib

open scoped Nat

theorem witness : ∃ n k : ℕ, 0 < k ∧ k * k ≤ n ∧ (n.choose k).minFac > n / k := by
  refine ⟨62, 6, by norm_num, by norm_num, ?_⟩
  have hc : Nat.choose 62 6 = 61474519 := by
    rw [Nat.choose_eq_descFactorial_div_factorial]
    norm_num [Nat.descFactorial, Nat.factorial]
  rw [hc]
  norm_num
