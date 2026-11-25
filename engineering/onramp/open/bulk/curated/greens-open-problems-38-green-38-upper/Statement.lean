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
import Defs.DataZModFp
import Defs.Local

/-! Green's Open Problem 38 — imported from google-deepmind/formal-conjectures (FormalConjectures/GreensOpenProblems/38.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); adapted from `green_38.upper`: the registry's `green_38.upper.answer` (defined as `sorry`) is bound by an existential `∃ U : ℕ → ℝ`, so the statement says the largest admissible set is `O(c^n)` for some `c` below Lovász's `C₂`, i.e. the Shannon capacity of the 7-cycle is strictly below its Lovász theta (F11-Q24, the registry's conjectured direction); the names it takes from its file (`LargestAdmissibleCardinality`, `C₂`) and the registry's library (`𝔽₇`) are ported under defs/ (R12). Curated by hand (curator C) and read by the lead before import (R13). -/

open Filter Set
open scoped Pointwise
open Green38

theorem Opn.upper :
    ∃ U : ℕ → ℝ,
    LargestAdmissibleCardinality ≤ᶠ[atTop] U ∧
    ∃ c : ℝ, 0 < c ∧ c < C₂ ∧ U =O[atTop] (fun n ↦ c ^ n) := by
  sorry
