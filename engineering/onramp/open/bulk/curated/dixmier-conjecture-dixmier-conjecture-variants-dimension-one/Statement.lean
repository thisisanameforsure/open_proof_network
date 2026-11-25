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
import Defs.Local

/-! The Dixmier Conjecture in dimension one, DC₁ — Problem 1 of Dixmier (1968), the registry's `dixmier_conjecture.variants.dimension_one`: over a field of characteristic zero, every endomorphism of the first Weyl algebra A₁(K) is an automorphism — imported from google-deepmind/formal-conjectures (FormalConjectures/Arxiv/math.0608009/DixmierConjecture.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); stated as the registry states it, with the file's section variables as binders; the definitions are ported under defs/ (R12). The Dixmier conjecture in all dimensions is false (DC_n fails for every n ≥ 3); n = 1 is Dixmier's own open problem. -/

open Arxiv.«math.0608009»

theorem Opn.dixmier_conjecture_dimension_one {K : Type*} [Field K] [CharZero K] :
    DixmierConjectureFor K 1 := by
  sorry
