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
import Defs.CombinatoricsSimpleGraphCircumference
import Defs.CombinatoricsSimpleGraphClique
import Defs.CombinatoricsSimpleGraphColoringVertex
import Defs.DataNatPrimeFinset
import Defs.FieldTheoryMilnorKTheory
import Defs.GroupTheoryRationalClasses
import Defs.Local

/-! Erdős problem 883, part i: For $A\subseteq \{1,\ldots,n\}$ let $G(A)$ be the graph with vertex set $A$, where two integers are joined by an edge if they are coprime. — imported from google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/883.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); stated as the registry states it; the names it takes from its file or the registry's library are ported mechanically under defs/ (R12, F14-T19). Drafted by gate/tools/wave.py (F14-T11) and read by the curator before import (R13). -/

open Filter
open scoped Classical
open Erdos883

theorem Opn.erdos_883 :
    ∀ (n : ℕ) (A : Finset ℕ),
      A ⊆ Finset.Icc 1 n →
      n / 2 + n / 3 - n / 6 < A.card →
      ∀ l : ℕ, Odd l → 3 ≤ l → l ≤ n / 3 + 1 →
        l ∈ (coprimeGraph.induce (A : Set ℕ)).oddCycleLengths := by
  sorry
