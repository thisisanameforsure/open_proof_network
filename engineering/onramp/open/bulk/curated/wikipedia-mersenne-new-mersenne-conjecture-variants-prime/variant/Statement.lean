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
import Defs.AlgebraWeylAlgebra
import Defs.AnalysisSpecialFunctionsAdditiveCharacter
import Defs.FieldTheoryMilnorKTheory
import Defs.GroupTheoryRationalClasses
import Defs.Local

/-! Conjectures about Mersenne primes, variant `new_mersenne_conjecture.variants.prime` — imported from google-deepmind/formal-conjectures (FormalConjectures/Wikipedia/Mersenne.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); stated as the registry states it: the New Mersenne Conjecture for odd primes p. A D-30 variant of the root `new-mersenne-conjecture` (all odd p), to which it is equivalent: the registry's own `new_mersenne_conjecture_of_prime` derives the root from it. -/

open Mersenne

theorem Opn.new_mersenne_conjecture_prime (p : ℕ) (hp : p.Prime) (h : Odd p) :
    NewMersenneConjectureStatement p := by
  sorry
