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
import Defs.DataZModFp

/-! Ported from `FormalConjectures/GreensOpenProblems/38.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by hand (curator C), in the form gate/tools/wave.py (F14-T19) gives a problem file: the file's own definitions, without the conjectures it states and their tests, and without `green_38.upper.answer`, whose registry body is a placeholder term rather than a definition (the adapted statement binds its own function instead). The module syntax is stripped so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

/-!
# Green's Open Problem 38

*References:*
- [100 open problems](https://people.maths.ox.ac.uk/greenbj/papers/open-problems.pdf#problem.38)
- [La79] Lovász, László. "On the Shannon capacity of a graph."
  IEEE Transactions on Information theory 25.1 (1979): 1-7.
- [Po20] Polak, Sven. "New methods in coding theory: Error-correcting codes and the Shannon capacity."
  arXiv preprint arXiv:2005.02945 (2020).
- [IRCR26] Itty, Nathaniel and Rosin, Christopher D. and Carstensen, Chase and Reichman, Daniel.
  "Improved lower bounds for the Shannon capacity of odd cycles." arXiv:2607.21517 (2026).
- [Ga26] Gao, Yu. "A recursive construction improving the lower bound on the Shannon capacity of
  $C_7$." arXiv:2607.27869 (2026).
- [BPZ26] Buys, Pjotr and Polak, Sven and Zuiddam, Jeroen. "Lean-verified lower bounds for the
  Shannon capacity of odd cycles." arXiv:2607.29681 (2026). Lean formalisation:
  https://github.com/spectra-research/shannon-capacity-lean
-/

section

open Filter Set
open scoped Pointwise

namespace Green38

/-- $A - A$ intersects $\{-1, 0, 1\}^n$ only at $0$. -/
def IntersectsOnlyAtZero {n : ℕ} (A : Finset (𝔽₇ n)) : Prop :=
  ∀ a ∈ A - A, (∀ i, a i ∈ ({-1, 0, 1} : Finset (ZMod 7))) → a = 0

/-- The set of cardinalities of all subsets A where A - A intersects {-1, 0, 1}^n only at 0. -/
def ValidCardinalities (n : ℕ) : Set ℕ :=
  { (A.card) | (A : Finset (𝔽₇ n)) (_ : IntersectsOnlyAtZero A) }

/--
The largest subset $A \subset \mathbb{F}_7^n$ for which $A - A$ intersects $\{-1, 0, 1\}^n$ only
at $0$.
-/
noncomputable def LargestAdmissibleCardinality : ℕ → ℝ := fun n ↦
  (sSup (ValidCardinalities n) : ℕ)

/-- The lower bound constant $C_1 \approx 3.2578$ from [Po20]. -/
noncomputable def C₁ : ℝ := (367 : ℝ) ^ (5⁻¹ : ℝ)

/-- The upper bound constant $C_2 \approx 3.3177$ from [La79]. -/
noncomputable def C₂ : ℝ := (7 * Real.cos (Real.pi / 7)) / (1 + Real.cos (Real.pi / 7))

def green_38.lower.answer : ℕ → ℝ := fun n : ℕ ↦ (134753 : ℝ) ^ (n / 10)

end Green38
