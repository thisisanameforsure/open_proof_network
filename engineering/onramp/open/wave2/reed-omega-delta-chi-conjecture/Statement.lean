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
import Defs.Clique
import Defs.Degrees

/-! Reed's omega, delta, and chi conjecture — imported from google-deepmind/formal-conjectures (FormalConjectures/Paper/ReedOmegaDeltaChi.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); stated as the registry states it; the names it takes from the registry's library are ported under defs/ (R12). Drafted by gate/tools/wave.py (F14-T11) and read by the curator before import (R13). -/

open scoped Finset

theorem Opn.reed_omega_delta_chi_conjecture :
    ∀ {V : Type} (G : SimpleGraph V),
    let χ := G.chromaticNumber
    let ω := G.ecliqueNum
    let Δ := G.emaxDegree
    2 * χ ≤ ω + Δ + 2 := by
  sorry
