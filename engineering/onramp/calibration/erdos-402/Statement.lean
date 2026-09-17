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

/-! Erdős problem 402 (calibration): a known result — imported from google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/402.lean at c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae, Apache-2.0); restated by hand (binders before the colon: the witness is not `True`, write it by hand). A calibration target (Stages v3.17, F15-R14): a known result, drafted by docs/calibration_pool.py and read by the curator before intake. -/

open Filter

theorem Opn.erdos_402 :
    ∀ (A : Finset ℕ), 0 ∉ A → A.Nonempty → ∃ᵉ (a ∈ A) (b ∈ A), a.gcd b ≤ (a / A.card : ℚ) := by
  sorry
