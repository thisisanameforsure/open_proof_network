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
import Defs.AnalysisAsymptoticsBasic
import Defs.CombinatoricsAdditiveRestrictedSumset

/-! Ported from `FormalConjectures/GreensOpenProblems/25.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by hand (curator C), in the form gate/tools/wave.py (F14-T19) gives a problem file: the file's own definitions, without the conjectures it states and their tests, and without `green_25.answer`, `green_25.upper.answer` and `green_25.lower.answer`, whose registry body is a placeholder term rather than a definition (the adapted statement binds its own function instead). The module syntax is stripped so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

/-!
# Green's Open Problem 25

References:
- [Gr24] [Green, Ben. "100 open problems." (2024).](https://people.maths.ox.ac.uk/greenbj/papers/open-problems.pdf#problem.25)
- [ESS89] Erdős, Pál, András Sárközy, and V. T. Sós. "On a conjecture of Roth and some related
  problems I." Irregularities of partitions. Berlin, Heidelberg: Springer Berlin Heidelberg, 1989.
  47-59.
- [Ru04] Ruzsa, Imre Z. "A problem on restricted sumsets." CONTEMPORARY MATHEMATICS 342 (2004):
  245-248.
-/

section

open Asymptotics Filter Finset

namespace Green25

/--
For which values of $k$ is the following true: whenever we partition $[N] = A_1 \cup \dots \cup A_k$,
$\left|\bigcup^k_{i=1} (A_i \hat{+} A_i)\right| \geq \frac{1}{10} N$?
-/
def Property25 (k N : ℕ) : Prop :=
  1 ≤ k ∧ k ≤ N ∧
  ∀ P : Finpartition (Icc 1 N), #P.parts = k →
  10 * #(P.parts.biUnion Finset.restrictedSumset) ≥ N

/-- The best-known lower bound [ESS89]. -/
noncomputable def bestLower (N : ℕ) : ℝ := Real.log (Real.log N)

/-- The best-known upper bound [ESS89]. -/
noncomputable def bestUpper (N : ℕ) : ℝ := (N : ℝ) / Real.log N

end Green25
