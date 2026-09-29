/-
Copyright 2026 The Formal Conjectures Authors.

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
import Nodes.«erdos-1050».Context

/-! Erdős problem 1050 (calibration): a known result — imported from google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/1050.lean at c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae, Apache-2.0); as stated. A calibration target (Stages v3.17, F15-R14): a known result, drafted by docs/calibration_pool.py and read by the curator before intake. -/

theorem Opn.erdos_1050 :
    Irrational (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 1) - 3)) := by
  -- The root's sum is its tail from n = 2: the terms at n = 0 and n = 1 are -1 and 1.
  have tail_summable : Summable (fun n : ℕ => (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) := by
    refine Summable.of_nonneg_of_le (fun n => ?_) (fun n => ?_)
      (summable_geometric_of_lt_one (by norm_num : (0:ℝ) ≤ 1/2) (by norm_num : (1/2:ℝ) < 1))
    · have h1 : (1:ℝ) ≤ 2 ^ n := one_le_pow₀ (by norm_num)
      have h2 : (2:ℝ) ^ (n + 3) = 8 * 2 ^ n := by ring
      apply div_nonneg zero_le_one
      rw [h2]; linarith
    · have h1 : (1:ℝ) ≤ 2 ^ n := one_le_pow₀ (by norm_num)
      have h2 : (2:ℝ) ^ (n + 3) = 8 * 2 ^ n := by ring
      rw [h2, one_div_pow]
      exact one_div_le_one_div_of_le (by positivity) (by linarith)
  have root_sum_eq_tail :
      ∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 1) - 3) = ∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3) := by
    have hs' : Summable (fun n : ℕ => (1 : ℝ) / ((2 : ℝ) ^ (n + 1) - 3)) := by
      refine (summable_nat_add_iff 2).mp ?_
      convert tail_summable using 2 with n
    rw [← hs'.sum_add_tsum_nat_add 2]
    norm_num [Finset.sum_range_succ]
  -- Integer approximants b n * T - a n, nonzero and tending to 0, make T irrational.
  have irrational_of_approximants (T : ℝ)
      (h : ∃ a b : ℕ → ℤ, (∀ n : ℕ, (b n : ℝ) * T - a n ≠ 0) ∧
        Filter.Tendsto (fun n : ℕ => (b n : ℝ) * T - a n) Filter.atTop (nhds 0)) :
      Irrational T := by
    obtain ⟨a, b, hne, ht⟩ := h
    rintro ⟨q, rfl⟩
    have hd : (0 : ℝ) < q.den := by exact_mod_cast q.den_pos
    obtain ⟨N, hN⟩ := (Metric.tendsto_atTop.mp ht) (1 / q.den) (by positivity)
    have hlt := hN N le_rfl
    rw [Real.dist_eq, sub_zero] at hlt
    set m : ℤ := b N * q.num - a N * q.den with hmdef
    have hm : (b N : ℝ) * q - a N = m / q.den := by
      rw [eq_div_iff hd.ne', hmdef, Rat.cast_def]
      push_cast
      field_simp
    have hm0 : m ≠ 0 := by
      intro h0; apply hne N; rw [hm, h0]; simp
    have h1 : (1 : ℝ) ≤ |(m : ℝ)| := by exact_mod_cast Int.one_le_abs hm0
    rw [hm, abs_div, abs_of_pos hd] at hlt
    rw [div_lt_div_iff_of_pos_right hd] at hlt
    linarith
  rw [root_sum_eq_tail]
  exact irrational_of_approximants _ erdos_1050__h1

