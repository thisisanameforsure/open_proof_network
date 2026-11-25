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
import Defs.AnalysisAsymptoticsBasic
import Defs.CombinatoricsAdditiveRestrictedSumset
import Defs.Local

/-! Green's Open Problem 25 — imported from google-deepmind/formal-conjectures (FormalConjectures/GreensOpenProblems/25.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); adapted from `green_25.lower`: the registry's `green_25.lower.answer` (defined as `sorry`) is bound by an existential `∃ L : ℕ → ℝ`, so the statement says the threshold `log log N` of [ESS89] can be raised beyond every constant multiple (F11-Q24, the registry's conjectured direction); the names it takes from its file (`Property25`, `bestLower`) and the registry's library (`Finset.restrictedSumset`, `≪`) are ported under defs/ (R12). Curated by hand (curator C) and read by the lead before import (R13). -/

open Asymptotics Filter Finset
open Green25

theorem Opn.lower :
    ∃ L : ℕ → ℝ,
    (bestLower =o[atTop] L) ∧
    (∀ᶠ N in atTop, 1 ≤ L N ∧ L N ≤ N) ∧
    ∀ k : ℕ → ℕ,
      (∀ᶠ N in atTop, 1 ≤ k N ∧ k N ≤ N) ∧
      ((fun N => (k N : ℝ)) ≪ L) →
      ∀ᶠ N in atTop, Property25 (k N) N := by
  sorry
