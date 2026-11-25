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

/-! Ported mechanically from `FormalConjecturesForMathlib/Data/Set/Interval.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by gate/tools/wave.py (F14-T19): the module `FormalConjecturesForMathlib.Data.Set.Interval`, lemmas included. The module syntax is stripped so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

variable {β : Type*} [Preorder β]
variable {S : Set β} {a b : β}

namespace Set

noncomputable instance [LocallyFiniteOrderBot β] : Fintype (S ∩ Iio b : Set β) :=
  (Set.finite_Iio b |>.inter_of_right S).fintype

noncomputable instance [LocallyFiniteOrder β] [OrderBot β] : Fintype (S ∩ Icc a b : Set β) :=
  (Set.finite_Icc a b |>.inter_of_right S).fintype

end Set
