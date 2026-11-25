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

/-! Ported mechanically from `FormalConjecturesForMathlib/GroupTheory/RationalClasses.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by gate/tools/wave.py (F14-T19): the module `FormalConjecturesForMathlib.GroupTheory.RationalClasses`, lemmas included. The module syntax is stripped so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

section

/-!
# Rational classes and Galois-stable conjugacy classes

The absolute Galois group of `ℚ` acts on the conjugacy classes of a finite group `G`: it maps the
class of `g` to the class of `g ^ k` for `k` coprime to the order of `g`.

* `Group.numRationalClasses G`: the number of orbits of this action on the conjugacy classes, the
  rational classes; two elements are in the same rational class exactly when they generate
  conjugate cyclic subgroups, so this is the number of conjugacy classes of cyclic subgroups;
* `Group.numGaloisStableClasses G`: the number of conjugacy classes fixed by the action, the
  classes on which every complex character of `G` takes rational values.
-/

open scoped Pointwise

namespace Group

variable (G : Type*) [Group G]

/-- The number of rational classes of `G`, the conjugacy classes of its cyclic subgroups. -/
noncomputable def numRationalClasses : ℕ :=
  (Set.range fun g : G => MulAction.orbit (ConjAct G) (Subgroup.zpowers g)).ncard

/-- The number of conjugacy classes of `G` that contain `g ^ k` together with `g` for every `k`
coprime to the order of `g`. -/
noncomputable def numGaloisStableClasses : ℕ :=
  ((ConjClasses.mk : G → ConjClasses G) ''
    {g : G | ∀ k : ℕ, k.Coprime (orderOf g) → IsConj g (g ^ k)}).ncard

instance [Finite G] : Finite (ConjClasses G) :=
  Finite.of_surjective _ ConjClasses.mk_surjective

theorem numGaloisStableClasses_le [Finite G] :
    numGaloisStableClasses G ≤ Nat.card (ConjClasses G) :=
  Set.ncard_le_card _

end Group
