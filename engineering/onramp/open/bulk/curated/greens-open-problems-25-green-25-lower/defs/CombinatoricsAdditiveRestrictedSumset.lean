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

/-! Ported mechanically from `FormalConjecturesForMathlib/Combinatorics/Additive/RestrictedSumset.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by gate/tools/wave.py (F14-T19): the module `FormalConjecturesForMathlib.Combinatorics.Additive.RestrictedSumset`, lemmas included. The module syntax is stripped so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

section

/-!
# Restricted sumsets

This file defines the restricted sumset $S \hat{+} S$ for a finite set $S$.
-/

namespace Finset

variable {α : Type*} [Add α] [DecidableEq α]

/--
The restricted sumset of a set $S$, denoted $S \hat{+} S$, is the set
$\lbrace s_1 + s_2 : s_1, s_2 \in S, s_1 \neq s_2 \rbrace$.
-/
def restrictedSumset (S : Finset α) : Finset α :=
  S.offDiag.image (fun p => p.1 + p.2)

end Finset
