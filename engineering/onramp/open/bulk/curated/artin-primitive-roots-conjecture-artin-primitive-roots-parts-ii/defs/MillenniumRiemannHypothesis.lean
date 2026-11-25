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
import Defs.NumberTheoryDirichletCharacterBasic

/-! Ported by hand from `FormalConjectures/Millennium/RiemannHypothesis.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by curator B: the file's own definitions, without the conjectures it states and their tests; the statement opens its namespace `GRH`. The module syntax is stripped (`module`, `public import`, `@[expose] public section`) so the gate elaborates it under `import Mathlib`; nothing else is changed. -/


/-!
# Riemann Hypothesis and its generalizations

The Riemann Hypothesis asserts that all non-trivial zeros of the Riemann zeta function
$\zeta(s)$ have real part $\frac{1}{2}$. The trivial zeros are the negative even integers
$-2, -4, -6, \ldots$. The hypothesis is one of the seven Millennium Prize Problems
posed by the Clay Mathematics Institute.

The Generalized Riemann Hypothesis extends this to Dirichlet $L$-functions of primitive
Dirichlet characters.

Note: the **Extended Riemann Hypothesis** (ERH) for Dedekind zeta functions is intentionally
**not** stated here. Mathlib's `NumberField.dedekindZeta` is the naive Dirichlet series
(`LSeries`), not a meromorphic continuation; outside the region of absolute convergence
`tsum` returns junk `0`, producing spurious zeros that make the naive foramlisation of the
conjecture provably false. The ERH should be added once Mathlib provides a meromorphic
continuation of the Dedekind zeta function.

*References:*
- [The Clay Institute](https://www.claymath.org/wp-content/uploads/2022/05/riemann.pdf)
- [Wikipedia: Riemann hypothesis](https://en.wikipedia.org/wiki/Riemann_hypothesis)
- [Wikipedia: Generalized Riemann hypothesis](https://en.wikipedia.org/wiki/Generalized_Riemann_hypothesis)
- [Wikipedia: Dedekind zeta function](https://en.wikipedia.org/wiki/Dedekind_zeta_function)
- J. Neukirch, *Algebraic Number Theory*, Springer (Grundlehren 322), 1999, Chapter VII, §5.
- D. A. Marcus, *Number Fields*, Springer (GTM 81), 1977, Chapter VII.
-/

section

namespace RiemannHypothesis

end RiemannHypothesis

namespace GRH

/-- Let $\chi$ be a Dirichlet character, `trivialZeros` is the set of trivial zeros of the
Dirichlet $L$-function of $\chi$ which is always a set of non-positive integers.
- $\chi = 1$ then the Dirichlet $L$-function is the Riemann zeta function, having trivial
  zeroes at all negative even integers (exclude $0$).
- $\chi$ is odd, then the trivial zeroes are the negative odd integers.
- $\chi \neq 1$ is even, then the trivial zeroes are the non-positive even integers. -/
def trivialZeros {q : ℕ} (χ : DirichletCharacter ℂ q) : Set ℤ :=
  if q = 1 then {-2 * (n + 1) | (n : ℕ) } else
    if χ.Odd then { -2 * n - 1 | (n : ℕ) } else
      { - 2 * n | (n : ℕ) }

end GRH

/- NOTE: Extended Riemann Hypothesis
## Extended Riemann Hypothesis

The ERH for Dedekind zeta functions **cannot** currently be stated correctly because
`NumberField.dedekindZeta` in Mathlib is the naive `LSeries`, not the meromorphic
continuation.  Outside the region of absolute convergence (`re s > 1`), `tsum` returns
junk `0` for non-summable series.  A statement using the raw `dedekindZeta` therefore has
spurious "zeros" that make the conjecture provably **false**.

A correct formalisation requires a meromorphic continuation of the Dedekind zeta function
(analogous to how `ZMod.LFunction` extends the Dirichlet L-series).  Once Mathlib provides
this, the ERH should be added back here.
-/
