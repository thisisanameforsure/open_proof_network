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

theorem Opn.erdos_68 :
    Irrational (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) := by
  -- approach: route 1 (erdos-68@1) with the tail of N!·S pinned between 1/(N+1) and 1/N, so the window the finite part's fractional part must avoid shrinks from width 2/N to 1/(N(N+1)) and the open core is strictly weaker
  -- licence: CC-BY-4.0
  -- label: factorial-multiplier criterion for irrationality
  -- claim: $\forall x\in\mathbb{R}:\ \big(\forall M\ \exists N\ge M\ \forall m\in\mathbb{Z},\ N!\,x\ne m\big)\Rightarrow x\notin\mathbb{Q}$
  have h1 : ∀ x : ℝ, (∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧ ∀ m : ℤ, (N.factorial : ℝ) * x ≠ m) →
      Irrational x := sorry
  -- label: N!·S = F_N + c with 1/(N+1) < c < 1/N for N ≥ 4
  -- claim: $\forall N\ge 4\ \exists c:\ \tfrac{1}{N+1}<c<\tfrac{1}{N}\ \text{and}\ N!\sum_{n\ge 2}\frac{1}{n!-1}=\sum_{n=2}^{N}\frac{N!}{n!-1}+c$
  have h2 : ∀ N : ℕ, 4 ≤ N → ∃ c : ℝ, 1 / ((N : ℝ) + 1) < c ∧ c < 1 / N ∧
      (N.factorial : ℝ) * (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) =
        (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) + c := sorry
  -- label: fract(F_N) avoids the window (1-1/N, 1-1/(N+1))
  -- claim: $\forall M\ \exists N\ge M:\ \{F_N\}\le 1-\tfrac{1}{N}\ \text{or}\ \{F_N\}\ge 1-\tfrac{1}{N+1},\ \text{where}\ F_N=\sum_{n=2}^{N}\frac{N!}{n!-1}$
  have h3 : ∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧
      (Int.fract (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) ≤ 1 - 1 / N ∨
        1 - 1 / ((N : ℝ) + 1) ≤
          Int.fract (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1))) := sorry
  apply h1
  intro M
  obtain ⟨N, hMN, hfr⟩ := h3 (max M 4)
  refine ⟨N, le_trans (le_max_left _ _) hMN, ?_⟩
  intro m hm
  have hN4 : 4 ≤ N := le_trans (le_max_right _ _) hMN
  obtain ⟨c, hc0, hc1, hS⟩ := h2 N hN4
  set F := ∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1) with hFdef
  have hNpos : (0 : ℝ) < N := by exact_mod_cast (by omega : 0 < N)
  have hF : F + c = m := by rw [← hS, hm]
  have h0 : 0 ≤ Int.fract F := Int.fract_nonneg F
  have h1' : Int.fract F < 1 := Int.fract_lt_one F
  have key : Int.fract F + c = ((m - ⌊F⌋ : ℤ) : ℝ) := by
    rw [Int.fract]; push_cast; linarith
  have hcpos : 0 < c := lt_trans (by positivity) hc0
  have hc1' : c < 1 := lt_of_lt_of_le hc1 (by rw [div_le_one hNpos]; exact_mod_cast (by omega : 1 ≤ N))
  have hk : m - ⌊F⌋ = 1 := by
    have a : ((m - ⌊F⌋ : ℤ) : ℝ) < 2 := by rw [← key]; linarith
    have b : (0 : ℝ) < ((m - ⌊F⌋ : ℤ) : ℝ) := by rw [← key]; linarith
    have a' : m - ⌊F⌋ < 2 := by exact_mod_cast a
    have b' : 0 < m - ⌊F⌋ := by exact_mod_cast b
    omega
  rw [hk] at key
  push_cast at key
  rcases hfr with h | h <;> linarith
