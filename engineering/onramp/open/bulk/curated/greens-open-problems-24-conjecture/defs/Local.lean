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

/-! Ported from `FormalConjectures/GreensOpenProblems/24.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by hand (curator C), in the form gate/tools/wave.py (F14-T19) gives a problem file: the file's own definitions, without the conjectures it states and their tests, and without `green_24.answer`, whose registry body is a placeholder term rather than a definition and no statement imported from this file uses. The module syntax is stripped so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

/-!
# Green's Open Problem 24

References:
- [Green, Ben. "100 open problems." (2024).](https://people.maths.ox.ac.uk/greenbj/papers/open-problems.pdf#problem.24)
- [Aa19] Aaronson, James. "Maximising the number of solutions to a linear equation in a set of integers."
  Bulletin of the London Mathematical Society 51.4 (2019): 577-594.
- [HaL28] Hardy, G. H., and J. E. Littlewood. "Notes on the theory of series (VIII): an inequality."
  Journal of the London Mathematical Society 1.2 (1928): 105-110.
-/

section

open Filter

namespace Green24

/--
The maximum number of $\lbrace 0,1,3 \rbrace$ affine translates that a set of size $n$ can
contain.
-/
noncomputable def max013AffineTranslates (n : ℕ) : ℕ :=
  sSup { k |
    ∃ A : Finset ℤ,
      A.card = n ∧
      -- Iterate over (x,y) = (a, a + d) in A × A (x ≠ y), and check if a + 3d = x + 3(y - x) ∈ A
      k = ((A ×ˢ A).filter (fun (x, y) ↦ x ≠ y ∧ x + 3 * (y - x) ∈ A)).card
  }

/-  A collection of associated bounds and conjectured values. -/

namespace variants

/-- The asymptotic constant $\gamma$ defined in [Aa19] p.579. -/
noncomputable def gamma : ℝ :=
  limsup (fun n : ℕ => (max013AffineTranslates n : ℝ) / ((n : ℝ)^2)) atTop

end variants

end Green24
