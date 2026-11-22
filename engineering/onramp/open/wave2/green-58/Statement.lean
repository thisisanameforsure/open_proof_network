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
import Defs.Composite

/-! Ben Green's Open Problem 58 — imported from google-deepmind/formal-conjectures (FormalConjectures/GreensOpenProblems/58.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); stated as the registry states it; the names it takes from the registry's library are ported under defs/ (R12). Drafted by gate/tools/wave.py (F14-T11) and read by the curator before import (R13). -/

open scoped Pointwise

theorem Opn.green_58 :
    ∀ᶠ (N : ℕ) in Filter.atTop, ∀ᵉ (A ⊆ Finset.Icc 1 N) (B ⊆ Finset.Icc 1 N),
      (N : ℝ) ^ (0.49 : ℝ) ≤ (A.card : ℝ) →
      (N : ℝ) ^ (0.49 : ℝ) ≤ (B.card : ℝ) →
      ∃ m ∈ (A + B), m.Composite := by
  sorry
