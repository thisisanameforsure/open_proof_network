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
import Defs.FieldTheoryMilnorKTheory
import Defs.GroupTheoryRationalClasses
import Defs.Local

/-! Ben Green's Open Problem 76, variant `green_76.variants.exists_constant` — imported from google-deepmind/formal-conjectures (FormalConjectures/GreensOpenProblems/76.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); stated as the registry states it: is there a constant k such that every finite set A of points in the plane has a set A' of at most ⌊|A|/2⌋ points meeting every axis-parallel rectangle that contains at least k points of A (Pach–Tardos, Problem 5, in an equivalent form). A D-30 variant of the root `green-76`, which is the same with k = 1000. -/

open scoped Finset
open Green76

theorem Opn.green_76_exists_constant :
    ∃ k : ℕ, ∀ A : Finset (ℝ × ℝ), ∃ A', #A' ≤ #A / 2 ∧ HitsRichRectangles k A A' := by
  sorry
