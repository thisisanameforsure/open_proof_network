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

/-! Ported mechanically from `FormalConjectures/ErdosProblems/883.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by gate/tools/wave.py (F14-T19): the file's own definitions, without the conjectures it states and their tests. The module syntax is stripped so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

/-!
# Erdős Problem 883

*References:*
- [erdosproblems.com/883](https://www.erdosproblems.com/883)
- [ErSa97] Erdős, P. and Sárközy, G. N., On cycles in the coprime graph of integers.
  Electron. J. Combin. (1997), Research Paper 8.
- [Sa99] Sárközy, G. N., Complete tripartite subgraphs in the coprime graph of integers.
  Discrete Math. (1999), 227-238.
-/

section

open Filter

namespace Erdos883

/--
The coprime graph on $\mathbb{N}$: two integers are joined by an edge if they are coprime.
-/
def coprimeGraph : SimpleGraph ℕ :=
  SimpleGraph.fromRel Nat.Coprime

end Erdos883
