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
import Defs.CombinatoricsBasic

/-! Ported from `FormalConjectures/GreensOpenProblems/27.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by hand (curator C), in the form gate/tools/wave.py (F14-T19) gives a problem file: the file's own definitions, without the conjectures it states and their tests, and without `green_27.equivalent.answer` and `green_27.upper.answer`, whose registry body is a placeholder term rather than a definition (the adapted statement binds its own function instead). The module syntax is stripped so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

/-!
# Green's Open Problem 27

References:
- [Gr24] [Green, Ben. "100 open problems." (2024).](https://people.maths.ox.ac.uk/greenbj/papers/open-problems.pdf#problem.27)
- [Be23] Bedert, Benjamin. "On unique sums in Abelian groups." Combinatorica 44.2 (2024): 269-298.
- [CY26] Cao, Jiao-Long, and Ye Yuan. "A Second-Logarithm Lower Bound for Sets with No Unique
  Sums." arXiv preprint arXiv:2608.06728 (2026).
- [He26] He, Xinjie. "A near-quadratic lower bound for sets with no unique sums." Working draft
  (July 21, 2026):
  https://github.com/xinjiegit/ben_27_formalization/blob/f70352964007662e97a810c880abbfea1e2ea262/NUS_edited.tex.
  Its Lean 4 proof is registered as
  [PALOMAR-2026-08-18-000003](https://palomar-registry.org/entry.html?id=PALOMAR-2026-08-18-000003&version=1).
- [HY26] Hou, Jianfeng, and Kai Yang. "A near-quadratic lower bound for sets with no unique sums."
  arXiv preprint arXiv:2610.09349 (2026).
- [St76] Straus, E. G. "Differences of residues (mod p)." Journal of Number Theory 8.1 (1976): 40-42.
-/

section

open Asymptotics Filter

namespace Green27

/--
This is $m(p)$ in [Be23]: the size of the smallest set $A \subset \mathbb{Z} / p\mathbb{Z}$ (with
at least two elements) for which no element in the sumset $A + A$ has a unique representation.
-/
noncomputable def m (p : ℕ) : ℝ :=
  (sInf { (A.card) | (A : Finset (ZMod p)) (_ : 2 ≤ A.card) (_ : HasNoUniqueRepresentation A) } : ℝ)

/-- `atTop` restricted to prime numbers. -/
def primesAtTop : Filter ℕ := atTop ⊓ 𝓟 {p : ℕ | p.Prime}

/-- Bedert's lower bound [Be23, Theorem 3]. This was the best known bound when Green's list was
written; it has since been improved, see `green_27.lower`. -/
noncomputable def lowerBest (p : ℕ) : ℝ :=
  (Real.sqrt (Real.log (Real.log (Real.log (p : ℝ)))) /
   Real.log (Real.log (Real.log (Real.log (p : ℝ))))) * Real.log (p : ℝ)

/-- Best-known upper bound [Be23, Theorem 5]. -/
noncomputable def upperBest (p : ℕ) : ℝ := (Real.log (p : ℝ)) ^ 2

noncomputable def green_27.lower.answer : ℕ → ℝ := fun p ↦ Real.log p * Real.log (Real.log p)

end Green27
