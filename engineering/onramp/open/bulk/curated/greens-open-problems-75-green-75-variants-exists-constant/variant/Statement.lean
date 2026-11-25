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
import Defs.AlgebraWeylAlgebra
import Defs.AnalysisSpecialFunctionsAdditiveCharacter
import Defs.CombinatoricsSimpleGraphClique
import Defs.CombinatoricsSimpleGraphColoringVertex
import Defs.FieldTheoryMilnorKTheory
import Defs.GroupTheoryRationalClasses
import Defs.Local

/-! Ben Green's Open Problem 75, variant `green_75.variants.exists_constant` — imported from google-deepmind/formal-conjectures (FormalConjectures/GreensOpenProblems/75.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); stated as the registry states it: is there a constant C such that every finite set X ⊂ ℝ² with at least two points has a line through two points of X whose sides differ by at most C (Kupitz's question in the form of Conlon–Lim, Section 1). A D-30 variant of the root `green-75`, which is the same with C = 100. -/

open scoped Finset
open Green75

theorem Opn.green_75_exists_constant :
    ∃ C : ℕ, ∀ X : Finset (ℝ × ℝ), 2 ≤ #X →
      ∃ p ∈ X, ∃ q ∈ X, p ≠ q ∧ imbalance X p q ≤ C := by
  sorry
