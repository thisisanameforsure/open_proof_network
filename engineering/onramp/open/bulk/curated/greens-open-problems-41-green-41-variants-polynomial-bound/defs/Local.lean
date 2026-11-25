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

/-! Ported by hand from `FormalConjectures/GreensOpenProblems/41.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0): the file's own definitions `pyjamaSet`, `coveringCopies` and `minCopies`, byte for byte, without the conjectures it states and their tests. The file's `def green_41.answer : ℝ → ℕ := sorry` (the registry's placeholder for the unknown answer to the main question) is left out: a port may not carry `sorry`, and the variant ported here does not use it. The module syntax is stripped (`module`, `public import FormalConjecturesUtil`, `@[expose] public section` kept as a plain `section`) so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

/-!
# Ben Green's Open Problem 41

*References*
- [Gr24] [Ben Green's Open Problem 41](https://people.maths.ox.ac.uk/greenbj/papers/open-problems.pdf#problem.41)
- [Ma15] Manners, Freddie. "A solution to the pyjama problem." Inventiones mathematicae 202.1 (2015): 239-270.
- [KrLe25] Kravitz, Noah, and James Leng. "Quantitative pyjama." arXiv preprint arXiv:2510.17744 (2025).

-/

section

namespace Green41

open Complex Set Pointwise

/--
The pyjama set is the set of points in the complex plane whose real part is within $\varepsilon$ of
an integer.
-/
def pyjamaSet (ε : ℝ) : Set ℂ :=
  { z | ∃ k : ℤ, |z.re - (k : ℝ)| ≤ ε }

/-- The set of valid numbers of rotated copies of the pyjama set of width ε that cover the plane. -/
def coveringCopies (ε : ℝ) : Set ℕ :=
  { n : ℕ | ∃ (Θ : Finset ℝ), Θ.card = n ∧
    (⋃ θ ∈ Θ, exp (θ * I) • pyjamaSet ε) = univ }

/-- The minimal number of rotated copies of the pyjama set of width ε needed to cover the plane. -/
noncomputable def minCopies (ε : ℝ) : ℕ :=
  sInf (coveringCopies ε)

end Green41
