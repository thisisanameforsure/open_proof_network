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

/-! Ported by hand from `FormalConjecturesForMathlib/NumberTheory/DirichletCharacter/Basic.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by curator B: the module `FormalConjecturesForMathlib.NumberTheory.DirichletCharacter.Basic`, whole (two `DecidablePred` instances for `DirichletCharacter.Odd` and `.Even`, which `GRH.trivialZeros` needs to elaborate). The module syntax is stripped (`module`, `public import`, `@[expose] public section`) so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

section

namespace DirichletCharacter

instance {S : Type*} [DecidableEq S] [CommRing S] {m : ℕ} :
    DecidablePred (Odd (S := S) (m := m)) :=
  fun ψ ↦ decidable_of_iff (ψ (-1) = -1) <| by rfl

instance {S : Type*} [DecidableEq S] [CommRing S] {m : ℕ} :
    DecidablePred (Even (S := S) (m := m)) :=
  fun ψ ↦ decidable_of_iff (ψ (-1) = 1) <| by rfl

end DirichletCharacter
