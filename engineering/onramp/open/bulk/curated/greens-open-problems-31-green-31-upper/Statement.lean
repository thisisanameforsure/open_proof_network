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

/-! Ben Green's Open Problem 31 — imported from google-deepmind/formal-conjectures (FormalConjectures/GreensOpenProblems/31.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); adapted from `green_31.upper`: the registry's `green_31.upper.answer` (defined as `sorry`) is bound by an existential `∃ U : ℕ → ℝ`, so the statement says that for infinitely many `N`, `F N ≤ √N + c N^{1/4} + C` with some `c < 0.94349` (the [HZ26] constant), improving the upper bound at least for infinitely many `N` (F11-Q24, the registry's conjectured direction; it follows from Erdős's conjecture `F N = √N + O_ε(N^ε)`, live as erdos-30); the names it takes from its file (`F`) and the registry's library (`Finset.maxSidonSubsetCard`) are ported under defs/ (R12). Curated by hand (curator C) and read by the lead before import (R13). -/

open Filter
open Green31

theorem Opn.upper :
    ∃ U : ℕ → ℝ,
    (∃ᶠ N in atTop, F N ≤ U N) ∧
    ∃ c < (0.94349 : ℝ), ∃ C : ℝ, ∀ᶠ N in atTop, U N - Real.sqrt (N : ℝ) ≤ c *
      (N : ℝ) ^ (4⁻¹ : ℝ) + C := by
  sorry
