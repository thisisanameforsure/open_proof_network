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
import Defs.CombinatoricsAPBasic
import Defs.CombinatoricsBasic
import Defs.DataZModFp
import Defs.Local

/-! Ben Green's Open Problem 31 — imported from google-deepmind/formal-conjectures (FormalConjectures/GreensOpenProblems/31.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); adapted from `green_31.lower`: the registry's `green_31.lower.answer` (defined as `sorry`) is bound by an existential `∃ L : ℕ → ℝ`, so the statement says `F N - √N` is unbounded above along infinitely many `N`, breaking the `N^{1/2} + O(1)` lower bound at least for infinitely many `N` (F11-Q24, the registry's conjectured direction); the names it takes from its file (`F`) and the registry's library (`Finset.maxSidonSubsetCard`) are ported under defs/ (R12). Curated by hand (curator C) and read by the lead before import (R13). -/

open Filter
open Green31

theorem Opn.lower :
    ∃ L : ℕ → ℝ,
    -- Break the O(1) barrier
    Filter.Tendsto (fun N ↦ L N - Real.sqrt (N : ℝ)) atTop atTop ∧
    ∃ᶠ N in atTop, L N ≤ F N := by
  sorry
