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
import Defs.LinearAlgebraGeneralLinearGroup
import Defs.LinearAlgebraSpecialLinearGroup

/-! Margulis's conjecture on bounded diagonal orbits in SL_n(ℝ)/SL_n(ℤ) — imported from google-deepmind/formal-conjectures (FormalConjectures/Arxiv/2504.17644/Margulis.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); stated as the registry states `conjecture_1_1`, binders before the colon included; `Matrix.SpecialLinearGroup.diagonalSubgroup` and the module it rests on are ported under defs/ (R12). Curated by hand (curators A and M) and read by the lead before import (R13). -/

open Matrix SpecialLinearGroup
open scoped MatrixGroups

/-- Let `D` be the diagonal group of `SL_n(ℝ)` where n ≥ 3.
Then any relatively compact `D`-orbit in `SL_n(ℝ) / SL_n(ℤ)` is closed. -/
theorem Opn.conjecture_1_1 {n : ℕ} (hn : 3 ≤ n)
    (g : SL(n, ℝ) ⧸ Subgroup.map (map (Int.castRingHom ℝ)) ⊤)
    (hg : IsCompact <| closure (MulAction.orbit (diagonalSubgroup (Fin n) ℝ) g)) :
    IsClosed <| MulAction.orbit (diagonalSubgroup (Fin n) ℝ) g := by
  sorry
