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
import Defs.AlgebraOrderGroupPointwiseInterval
import Defs.DataSetDensity
import Defs.DataSetInterval
import Defs.Local
import Defs.MillenniumRiemannHypothesis
import Defs.NumberTheoryDirichletCharacterBasic
import Defs.OrderIntervalFinsetBasic
import Defs.OrderIntervalFinsetNat

/-! Artin's conjecture on primitive roots — imported from google-deepmind/formal-conjectures (FormalConjectures/Wikipedia/ArtinPrimitiveRootsConjecture.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); stated as the registry states `artin_primitive_roots.parts.ii`, binders before the colon included; the names it takes from its file (`S`, `ArtinConstant`), from the registry's library (`Set.HasDensity`) and the namespace `GRH` it opens from FormalConjectures/Millennium/RiemannHypothesis.lean are ported under defs/ (R12). Curated by hand (curator B) and read by the lead before import (R13). -/

open GRH
open scoped Topology Nat
open ArtinPrimitiveRootsConjecture

theorem Opn.ii
    (a a_0 b : ℤ) (ha : a = a_0 * b ^ 2)
    (ha' : ∀ n m, m ≠ 1 → a ≠ n ^ m) (ha_0 : Squarefree a_0)
    (ha_0' : ¬a_0 ≡ 1 [ZMOD 4]) :
    (S a).HasDensity ArtinConstant {p | p.Prime} := by
  sorry
