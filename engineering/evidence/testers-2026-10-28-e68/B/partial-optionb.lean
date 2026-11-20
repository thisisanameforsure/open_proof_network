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

/-! Erdős problem 68 — erdosproblems.com/68, imported from
google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/68.lean at
c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae, Apache-2.0), adapted to D-3's shape: the
registry states a yes/no question as `answer(sorry) ↔ P`; this states P, its affirmative
reading (F11-Q24). Listed, not claimable, at Stage 0. -/

private theorem B_fact_ge (K j : ℕ) :
    ((K.factorial : ℝ) * ((K : ℝ) + 1) ^ (j + 1)) ≤ ((j + K + 1).factorial : ℝ) := by
  have h := Nat.factorial_mul_pow_le_factorial (m := K) (n := j + 1)
  have he : K + (j + 1) = j + K + 1 := by omega
  rw [he] at h
  exact_mod_cast h

private theorem B_tail_term (K j : ℕ) (hK : 1 ≤ K) :
    (K.factorial : ℝ) * (1 / (((j + K + 1).factorial : ℝ) - 1)) ≤
      (1 / (K : ℝ)) * (1 / ((K : ℝ) + 1)) ^ j := by
  have hKr : (1:ℝ) ≤ K := by exact_mod_cast hK
  have hf := B_fact_ge K j
  have hKf : (1:ℝ) ≤ (K.factorial : ℝ) := by exact_mod_cast Nat.one_le_iff_ne_zero.mpr (Nat.factorial_ne_zero K)
  have hp : (K + 1 : ℝ) ≤ ((K : ℝ) + 1) ^ (j + 1) := by
    calc (K + 1 : ℝ) = ((K:ℝ) + 1) ^ 1 := by ring
      _ ≤ ((K : ℝ) + 1) ^ (j + 1) := pow_le_pow_right₀ (by linarith) (by omega)
  -- m! - 1 ≥ m! * K/(K+1) since m! ≥ K+1
  have hm1 : ((K : ℝ) + 1) ≤ ((j + K + 1).factorial : ℝ) := by nlinarith
  have hden : 0 < ((j + K + 1).factorial : ℝ) - 1 := by linarith
  have hpow : 0 < ((K : ℝ) + 1) ^ j := by positivity
  rw [div_pow, one_pow, mul_one_div, one_div_mul_one_div, div_le_div_iff₀ hden (by positivity)]
  -- K! * (K * (K+1)^j) ≤ m! - 1
  have : (K.factorial : ℝ) * ((K : ℝ) * ((K : ℝ) + 1) ^ j) * ((K:ℝ) + 1) ≤
      (((j + K + 1).factorial : ℝ) - 1) * ((K:ℝ) + 1) := by
    have e : (K.factorial : ℝ) * ((K : ℝ) * ((K : ℝ) + 1) ^ j) * ((K:ℝ) + 1)
        = (K : ℝ) * ((K.factorial : ℝ) * ((K : ℝ) + 1) ^ (j + 1)) := by ring
    rw [e]
    nlinarith
  nlinarith

private theorem B_tail_bound (K : ℕ) (hK : 1 ≤ K) :
    0 < (K.factorial : ℝ) * ∑' j : ℕ, 1 / (((j + K + 1).factorial : ℝ) - 1) ∧
      (K.factorial : ℝ) * ∑' j : ℕ, 1 / (((j + K + 1).factorial : ℝ) - 1) ≤
        ((K : ℝ) + 1) / (K : ℝ) ^ 2 := by
  have hKr : (1:ℝ) ≤ K := by exact_mod_cast hK
  have hpos : ∀ j : ℕ, 0 < ((j + K + 1).factorial : ℝ) - 1 := by
    intro j
    have : (2:ℕ) ≤ (j + K + 1).factorial := by
      have := Nat.factorial_le (show 2 ≤ j + K + 1 by omega)
      simpa using this
    have : (2:ℝ) ≤ ((j + K + 1).factorial : ℝ) := by exact_mod_cast this
    linarith
  have hKf : (0:ℝ) < (K.factorial : ℝ) := by exact_mod_cast Nat.factorial_pos K
  have hr : 1 / ((K : ℝ) + 1) < 1 := by
    rw [div_lt_one (by linarith)]; linarith
  have hgeo : Summable (fun j : ℕ => (1 / (K : ℝ)) * (1 / ((K : ℝ) + 1)) ^ j) :=
    (summable_geometric_of_lt_one (by positivity) hr).mul_left _
  have hle : ∀ j : ℕ, 1 / (((j + K + 1).factorial : ℝ) - 1) ≤
      (1 / (K.factorial : ℝ)) * ((1 / (K : ℝ)) * (1 / ((K : ℝ) + 1)) ^ j) := by
    intro j
    have := B_tail_term K j hK
    calc 1 / (((j + K + 1).factorial : ℝ) - 1)
        = (1 / (K.factorial : ℝ)) * ((K.factorial : ℝ) * (1 / (((j + K + 1).factorial : ℝ) - 1))) := by
          field_simp
      _ ≤ (1 / (K.factorial : ℝ)) * ((1 / (K : ℝ)) * (1 / ((K : ℝ) + 1)) ^ j) := by
          gcongr
  have hs : Summable (fun j : ℕ => 1 / (((j + K + 1).factorial : ℝ) - 1)) :=
    Summable.of_nonneg_of_le (fun j => (one_div_pos.mpr (hpos j)).le) hle (hgeo.mul_left _)
  constructor
  · apply mul_pos hKf
    exact hs.tsum_pos (fun j => (one_div_pos.mpr (hpos j)).le) 0 (one_div_pos.mpr (hpos 0))
  · have h1 := hs.tsum_le_tsum hle (hgeo.mul_left _)
    rw [tsum_mul_left, tsum_mul_left, tsum_geometric_of_lt_one (by positivity) hr] at h1
    have hK0 : (K : ℝ) ≠ 0 := by linarith
    have hK1 : (K : ℝ) + 1 ≠ 0 := by linarith
    have hgs : (1 - 1 / ((K : ℝ) + 1))⁻¹ = ((K : ℝ) + 1) / K := by
      rw [one_sub_div hK1, inv_div]; ring
    rw [hgs] at h1
    calc (K.factorial : ℝ) * ∑' j : ℕ, 1 / (((j + K + 1).factorial : ℝ) - 1)
        ≤ (K.factorial : ℝ) * ((1 / (K.factorial : ℝ)) * ((1 / (K : ℝ)) * (((K : ℝ) + 1) / K))) := by
          gcongr
      _ = ((K : ℝ) + 1) / (K : ℝ) ^ 2 := by field_simp


private theorem B_summable :
    Summable (fun n : ℕ => 1 / ((n + 2).factorial - 1 : ℝ)) := by
  have hs : Summable (fun n : ℕ => 2 / ((n + 2).factorial : ℝ)) := by
    have := (Real.summable_pow_div_factorial 1)
    have h2 := (summable_nat_add_iff 2).mpr this
    simpa [div_eq_mul_inv] using h2.mul_left 2
  refine Summable.of_nonneg_of_le (fun n => ?_) (fun n => ?_) hs
  · have h : (2:ℕ) ≤ (n + 2).factorial := by
      simpa using Nat.factorial_le (show 2 ≤ n + 2 by omega)
    have h' : (2:ℝ) ≤ ((n + 2).factorial : ℝ) := by exact_mod_cast h
    exact (one_div_pos.mpr (by linarith)).le
  · have h : (2:ℕ) ≤ (n + 2).factorial := by
      simpa using Nat.factorial_le (show 2 ≤ n + 2 by omega)
    have h' : (2:ℝ) ≤ ((n + 2).factorial : ℝ) := by exact_mod_cast h
    rw [div_le_div_iff₀ (by linarith) (by linarith)]
    linarith

private theorem B_A_h2 : ∀ N : ℕ, 2 ≤ N → ∃ c : ℝ, 0 < c ∧ c ≤ 2 / N ∧
      (N.factorial : ℝ) * (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) =
        (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) + c := by
  intro N hN
  obtain ⟨h0, h1⟩ := B_tail_bound N (by omega)
  refine ⟨_, h0, le_trans h1 ?_, ?_⟩
  · have hN' : (2:ℝ) ≤ N := by exact_mod_cast hN
    rw [div_le_div_iff₀ (by positivity) (by positivity)]
    nlinarith
  · have hsplit := B_summable.sum_add_tsum_nat_add (N - 1)
    have he : ∀ i : ℕ, i + (N - 1) + 2 = i + N + 1 := fun i => by omega
    simp only [he] at hsplit
    rw [← hsplit, mul_add, Finset.mul_sum]
    congr 1
    have hI : Finset.Icc 2 N = Finset.Ico 2 (N + 1) := rfl
    rw [hI, Finset.sum_Ico_eq_sum_range, show N + 1 - 2 = N - 1 by omega]
    refine Finset.sum_congr rfl (fun k _ => ?_)
    rw [show 2 + k = k + 2 by omega, mul_one_div]

private theorem B_A_h1 : ∀ x : ℝ, (∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧ ∀ m : ℤ, (N.factorial : ℝ) * x ≠ m) →
      Irrational x := by
  intro x h
  rintro ⟨r, rfl⟩
  obtain ⟨N, hMN, hN⟩ := h r.den
  obtain ⟨k, hk⟩ := Nat.dvd_factorial r.den_pos hMN
  apply hN (k * r.num)
  have h1 : (r : ℝ) * r.den = r.num := by exact_mod_cast Rat.mul_den_eq_num r
  rw [hk]; push_cast; linear_combination (k : ℝ) * h1

theorem Opn.erdos_68 :
    Irrational (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) := by
  -- approach: multiply by N! as in the proof that e is irrational; N!·S is a finite sum F_N plus a tail in (0, 2/N]
  -- licence: CC-BY-4.0
  have h1 : ∀ x : ℝ, (∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧ ∀ m : ℤ, (N.factorial : ℝ) * x ≠ m) →
      Irrational x := B_A_h1
  have h2 : ∀ N : ℕ, 2 ≤ N → ∃ c : ℝ, 0 < c ∧ c ≤ 2 / N ∧
      (N.factorial : ℝ) * (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) =
        (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) + c := B_A_h2
  -- label: fractional parts of the factorial-scaled sums
  -- claim: $\forall M\ \exists N \ge M,\ \left\{\sum_{n=2}^{N} \frac{N!}{n!-1}\right\} < 1 - \frac{2}{N}$
  have h3 : ∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧
      Int.fract (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) <
        1 - 2 / N := sorry
  apply h1
  intro M
  obtain ⟨N, hMN, hfr⟩ := h3 (max M 2)
  refine ⟨N, le_trans (le_max_left _ _) hMN, ?_⟩
  intro m hm
  obtain ⟨c, hc0, hc2, hS⟩ := h2 N (le_trans (le_max_right _ _) hMN)
  set F := ∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1) with hFdef
  have hF : F + c = m := by rw [← hS, hm]
  have h0 : 0 ≤ Int.fract F := Int.fract_nonneg F
  have key : Int.fract F + c = ((m - ⌊F⌋ : ℤ) : ℝ) := by
    rw [Int.fract]; push_cast; linarith
  have hlt : Int.fract F + c < 1 := by linarith
  have hpos : 0 < Int.fract F + c := by linarith
  rw [key] at hlt hpos
  have hlt' : m - ⌊F⌋ < 1 := by exact_mod_cast hlt
  have hpos' : 0 < m - ⌊F⌋ := by exact_mod_cast hpos
  omega
