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
  -- annex: 60c3f96117863c5f8df64b6be6d5178d8de0e3ff7996bca4be9a4628810cb206
  -- approach: as in the proof that e is irrational: multiply by N!; a rational sum makes N!·S an integer for large N, and the finite part's fractional part must then sit in a window of width at most 2/N
  -- licence: CC-BY-4.0
  -- label: factorial-multiplier criterion for irrationality
  -- claim: $\forall x\in\mathbb{R}:\ \big(\forall M\ \exists N\ge M\ \forall m\in\mathbb{Z},\ N!\,x\ne m\big)\Rightarrow x\notin\mathbb{Q}$
  -- If x = p/q then N!·x is an integer for every N ≥ q. Elementary.
  have h1 : ∀ x : ℝ, (∀ M : ℕ, ∃ N : ℕ, M ≤ N ∧ ∀ m : ℤ, (N.factorial : ℝ) * x ≠ m) →
      Irrational x := sorry
  -- label: N!·S splits as a finite sum plus a tail in (0, 2/N]
  -- claim: $\forall N\ge 2\ \exists c,\ 0<c\le \tfrac{2}{N}\ \text{and}\ N!\sum_{n\ge 2}\frac{1}{n!-1}=\sum_{n=2}^{N}\frac{N!}{n!-1}+c$
  -- c = N!·Σ_{n>N} 1/(n!-1); since n!-1 ≥ n!/2, c ≤ 2·Σ_{j≥1} (N+1)^{-j} = 2/N. Elementary.
  have h2 : ∀ N : ℕ, 2 ≤ N → ∃ c : ℝ, 0 < c ∧ c ≤ 2 / N ∧
      (N.factorial : ℝ) * (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) =
        (∑ n ∈ Finset.Icc 2 N, (N.factorial : ℝ) / ((n.factorial : ℝ) - 1)) + c := sorry
  -- label: the finite sum's fractional part avoids [1-2/N, 1)
  -- claim: $\forall M\ \exists N\ge M:\ \operatorname{frac}\Big(\sum_{n=2}^{N}\frac{N!}{n!-1}\Big)<1-\frac{2}{N}$
  -- The open core. A finite statement about rationals with no analysis left in it, strictly stronger than
  -- the root: if S = p/q, the fractional part equals 1 - c with 0 < c ≤ 2/N for every N ≥ max(q, 2).
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
