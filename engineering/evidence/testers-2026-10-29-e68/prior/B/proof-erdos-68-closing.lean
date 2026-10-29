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
import Nodes.«erdos-68».Context

/-! Erdős problem 68 — erdosproblems.com/68, imported from
google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/68.lean at
c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae, Apache-2.0), adapted to D-3's shape: the
registry states a yes/no question as `answer(sorry) ↔ P`; this states P, its affirmative
reading (F11-Q24). Listed, not claimable, at Stage 0. -/

theorem Opn.erdos_68 :
    Irrational (∑' n : ℕ, 1 / ((n + 2).factorial - 1 : ℝ)) := by
  have h1 := erdos_68__h1
  have h2 := erdos_68__h2
  have h3 := erdos_68__h3
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
