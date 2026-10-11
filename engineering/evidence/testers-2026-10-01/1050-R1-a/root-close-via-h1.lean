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
  -- Through the hole `erdos_1050__h1` (node erdos-1050--h1-v2): integers a n, b n with
  -- e n = b n * T - a n nonzero and tending to 0, where T = ∑ 1/(2^(n+3) - 3).
  obtain ⟨a, b, hne, hlim⟩ := erdos_1050__h1
  -- The root's sum is T: its terms at n = 0, 1 are -1 and 1, and its tail from n = 2 is T.
  have hT : Summable (fun n : ℕ => (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) := by
    refine Summable.of_nonneg_of_le (fun n => ?_) (fun n => ?_) (summable_geometric_two.mul_left (1 / 4))
    · have h1 : (1 : ℝ) ≤ 2 ^ n := one_le_pow₀ (by norm_num)
      have h2 : (0 : ℝ) < 2 ^ (n + 3) - 3 := by rw [pow_add]; norm_num; linarith
      exact le_of_lt (one_div_pos.mpr h2)
    · have h1 : (1 : ℝ) ≤ 2 ^ n := one_le_pow₀ (by norm_num)
      have e : (1 / 4 : ℝ) * (1 / 2) ^ n = 1 / (4 * 2 ^ n) := by rw [one_div_pow]; field_simp
      rw [e, pow_add]
      exact one_div_le_one_div_of_le (by positivity) (by norm_num; linarith)
  have hroot : ∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 1) - 3) = ∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3) := by
    have hs : Summable (fun n : ℕ => (1 : ℝ) / ((2 : ℝ) ^ (n + 1) - 3)) :=
      (summable_nat_add_iff 2).mp (by simpa only [add_assoc] using hT)
    rw [← hs.sum_add_tsum_nat_add 2]
    norm_num [Finset.sum_range_succ, add_assoc]
  rw [hroot]
  -- If T = p/q, then q * e n is a nonzero integer for every n, yet it tends to 0.
  rintro ⟨r, hr⟩
  have hq : (0 : ℝ) < r.den := by exact_mod_cast r.den_pos
  have hint : ∀ n : ℕ, ((b n * r.num - a n * r.den : ℤ) : ℝ) =
      (r.den : ℝ) * ((b n : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - a n) := by
    intro n
    rw [← hr]
    have : (r : ℝ) = r.num / r.den := by exact_mod_cast (Rat.num_div_den r).symm
    rw [this]; push_cast; field_simp
  have h0 : Filter.Tendsto (fun n : ℕ => (r.den : ℝ) *
      ((b n : ℝ) * (∑' n : ℕ, (1 : ℝ) / ((2 : ℝ) ^ (n + 3) - 3)) - a n)) Filter.atTop (nhds 0) := by
    simpa using hlim.const_mul (r.den : ℝ)
  obtain ⟨N, hN⟩ := (Metric.tendsto_atTop.mp h0) 1 one_pos
  have hsmall := hN N le_rfl
  rw [Real.dist_eq, sub_zero, ← hint N] at hsmall
  have hnz : (b N * r.num - a N * r.den : ℤ) ≠ 0 := by
    intro hz
    apply hne N
    have h2 := hint N
    rw [hz, Int.cast_zero] at h2
    exact (mul_eq_zero.mp h2.symm).resolve_left hq.ne'
  have : (1 : ℝ) ≤ |((b N * r.num - a N * r.den : ℤ) : ℝ)| := by exact_mod_cast Int.one_le_abs hnz
  linarith
