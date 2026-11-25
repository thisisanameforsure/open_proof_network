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
import Defs.Local

/-! Ben Green's Open Problem 41, polynomial bound (the registry's `green_41.variants.polynomial_bound`): are ε^(−C) rotated copies of the pyjama set of width ε enough to cover the plane, for some C and all small ε > 0? — imported from google-deepmind/formal-conjectures (FormalConjectures/GreensOpenProblems/41.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); stated as the registry states it; the file's definitions are ported under defs/ (R12). -/

open Complex Set Pointwise
open Green41

theorem Opn.green_41_polynomial_bound :
    ∃ C : ℝ, ∃ ε₀ > 0, ∀ ε ∈ Ioc 0 ε₀, (minCopies ε : ℝ) ≤ ε ^ (-C) := by
  sorry
