import Mathlib
open Nat
/-! Audit of B's h_dw hole (BBdW Conj 2.1 as stated): the eight sporadic tuples are collisions and the
Lind member i = 1, 2 are collisions; each tuple meets 2 ≤ k ≤ n/2, 2 ≤ l ≤ m/2, k < l. -/
example : choose 78 2 = choose 15 5 ∧ choose 78 2 = choose 14 6 ∧ choose 16 2 = choose 10 3 ∧
    choose 21 2 = choose 10 4 ∧ choose 56 2 = choose 22 3 ∧ choose 120 2 = choose 36 3 ∧
    choose 153 2 = choose 19 5 ∧ choose 221 2 = choose 17 8 := by decide
example : fib 4 * fib 5 = 15 ∧ fib 2 * fib 5 = 5 ∧ fib 6 * fib 7 = 104 ∧ fib 4 * fib 7 = 39 := by decide
example : choose 15 5 = choose 14 6 := by decide
example : choose 104 39 = choose 103 40 := by
  rw [Nat.choose_eq_factorial_div_factorial (by norm_num), Nat.choose_eq_factorial_div_factorial (by norm_num)]
  norm_num [Nat.factorial]
-- side conditions of each sporadic tuple
example : (2 ≤ 2 ∧ 2 * 2 ≤ 78 ∧ 2 ≤ 5 ∧ 2 * 5 ≤ 15 ∧ 2 < 5) ∧ (2 * 6 ≤ 14 ∧ 2 < 6) ∧ (2 * 3 ≤ 10) ∧ (2 * 4 ≤ 10) ∧
    (2 * 3 ≤ 22) ∧ (2 * 3 ≤ 36) ∧ (2 * 5 ≤ 19) ∧ (2 * 8 ≤ 17) := by decide
