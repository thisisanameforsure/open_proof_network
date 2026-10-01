/-
Copyright 2025 The Formal Conjectures Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-/

import Mathlib

/-! Erdős problem 69 (calibration): a known result — imported from google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/69.lean at c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae, Apache-2.0); as stated. A calibration target (Stages v3.17, F15-R14): a known result, drafted by docs/calibration_pool.py and read by the curator before intake. -/

open scoped ArithmeticFunction.omega

theorem Opn.erdos_69 :
    Irrational <| ∑' n, ω (n + 2) / 2 ^ (n + 2) := by
  -- Hole 1 (Tao's remark under Erdős 257): the Lambert-series identity. Writing ω(n) as the
  -- number of primes dividing n and swapping the absolutely convergent double sum,
  -- ∑_n ω(n)/2^n = ∑_p ∑_{k ≥ 1} 2^{-pk} = ∑_p 1/(2^p - 1).
  have h_lambert : ∑' n : ℕ, (ω n : ℝ) / 2 ^ n
      = ∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1) := sorry
  -- Hole 2 (Erdős 1948): the prime sum ∑_p 1/(2^p - 1) is irrational.
  have h_irr : Irrational (∑' p : Nat.Primes, (1 : ℝ) / (2 ^ (p : ℕ) - 1)) := sorry
  -- Assembly: the statement's sum starts at n = 2, and ω 0 = ω 1 = 0, so it is the whole sum.
  have hbound : ∀ n : ℕ,
      (ω n : ℝ) / 2 ^ n ≤ (n : ℝ) ^ 1 * (1 / 2 : ℝ) ^ n + (1 / 2 : ℝ) ^ n := by
    intro n
    have h1 : ω n ≤ n + 1 := by
      rw [ArithmeticFunction.cardDistinctFactors_apply]
      calc n.primeFactorsList.dedup.length = n.primeFactors.card := rfl
        _ ≤ (Finset.range (n + 1)).card :=
            Finset.card_le_card (fun p hp =>
              Finset.mem_range.2 (Nat.lt_succ_of_le (Nat.le_of_mem_primeFactors hp)))
        _ = n + 1 := Finset.card_range _
    have h2 : (ω n : ℝ) ≤ (n : ℝ) + 1 := by exact_mod_cast h1
    have h4 : (0 : ℝ) ≤ ((2 : ℝ) ^ n)⁻¹ := by positivity
    rw [pow_one, one_div, inv_pow, div_eq_mul_inv]
    nlinarith [mul_le_mul_of_nonneg_right h2 h4]
  have hsum : Summable (fun n : ℕ => (ω n : ℝ) / 2 ^ n) := by
    refine Summable.of_nonneg_of_le (fun n => by positivity) hbound ?_
    exact (summable_pow_mul_geometric_of_norm_lt_one 1 (by norm_num [Real.norm_eq_abs])).add
      (summable_geometric_of_lt_one (by norm_num) (by norm_num))
  have hshift : ∑' n : ℕ, (ω (n + 2) : ℝ) / 2 ^ (n + 2) = ∑' n : ℕ, (ω n : ℝ) / 2 ^ n := by
    have h : ∑ i ∈ Finset.range 2, (ω i : ℝ) / 2 ^ i + ∑' i : ℕ, (ω (i + 2) : ℝ) / 2 ^ (i + 2)
        = ∑' i : ℕ, (ω i : ℝ) / 2 ^ i := hsum.sum_add_tsum_nat_add 2
    rw [← h]
    simp [Finset.sum_range_succ,
      ArithmeticFunction.cardDistinctFactors_one]
  rw [hshift, h_lambert]
  exact h_irr
