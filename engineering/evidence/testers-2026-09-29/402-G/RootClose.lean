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
import Nodes.«erdos-402».Context

/-! Erdős problem 402 (calibration): a known result — imported from google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/402.lean at c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae, Apache-2.0); restated by hand (binders before the colon: the witness is not `True`, write it by hand). A calibration target (Stages v3.17, F15-R14): a known result, drafted by docs/calibration_pool.py and read by the curator before intake. -/

open Filter

theorem Opn.erdos_402 :
    ∀ (A : Finset ℕ), 0 ∉ A → A.Nonempty → ∃ᵉ (a ∈ A) (b ∈ A), a.gcd b ≤ (a / A.card : ℚ) := by
  intro A hA hne
  have h1 := erdos_402__h1
  have h2 := erdos_402__h2 h1
  have h3 := erdos_402__h3 h1 h2
  refine h2 A hA hne ?_
  intro B hB hcard hg
  by_contra hcon
  push_neg at hcon
  have hBne : B.Nonempty := by
    rw [← Finset.card_pos, hcard]
    exact hne.card_pos
  have hbound : ∀ a ∈ B, ∀ b ∈ B, a ≤ B.card * a.gcd b := by
    intro a ha b hb
    have h := hcon a ha b hb
    have hpos : (0 : ℚ) < B.card := by exact_mod_cast hBne.card_pos
    have h' : (a : ℚ) < (a.gcd b : ℚ) * B.card := (div_lt_iff₀ hpos).mp h
    rw [mul_comm] at h'
    have h'' : a < B.card * a.gcd b := by exact_mod_cast h'
    exact h''.le
  obtain ⟨a, ha, b, hb, hle⟩ := h3 B hB hBne hg (h1 B B.card hB hbound)
  exact absurd hle (not_le.mpr (hcon a ha b hb))
