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
import Defs.MillenniumRiemannHypothesis

/-! Ported by hand from `FormalConjectures/Wikipedia/ArtinPrimitiveRootsConjecture.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by curator B: of the file's own definitions, the two the statements `artin_primitive_roots.parts.i` and `.parts.ii` use (`S`, `ArtinConstant`); `IsDedekindZeta`, `DedekindZetaRH`, `HooleyHypothesis`, `powCorrectionFactor` and `entanglementFactor` are left out because neither statement uses them (they serve the file's conditional and power variants), and the conjectures, tests and API lemma are left out as the mechanical port leaves them out. The module syntax is stripped (`module`, `public import`, `@[expose] public section`) so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

/-!
# Artin's conjecture on primitive roots

Artin's conjecture predicts, given an integer $a$, densities of primes $p$ for which
$a$ is a primitive root modulo $p$. Under certain conditions (when $a$ is not a
power and its squarefree part is not $1\pmod{4}$) the density is given by Artin's constant
$$\prod_{p\ \text{prime}} \left(1 - \frac{1}{p(p - 1)}\right).$$
For more general values of $a$, this constant must be corrected by certain factors.
- When $a = b^m$, $m$ is a maximal odd power, the squarefree part of $b$ satisfies
  $b_0 \not\equiv 1\pmod{4}$. Then Artin's constant should be multiplied by
  $$\prod_{p \mid m} \frac{p(p - 2)}{p^2 - p - 1}.$$
- When $a = b^m$, $m$ is a maximal power, the squarefree part of $b$ satisfies
  $b_0\equiv 1\pmod{4}$. Then Artin's constant should be multiplied by the factor in
  the above bullet, as well as an additional entanglement factor from the primes dividing
  $\gcd(b_0, m)$ and primes dividing $b_0$:
  $$1 - \prod_{p \mid \gcd(b_0, m)} \frac{1}{2 - p}
  \prod_{p \mid b_0, p\nmid m} \frac{1}{1 + p - p^2}.$$
- When $a = -1$ or $a$ is a square, then the density is $0$.

Note that Artin's conjecture has been proved by Hooley [Ho67] subject to the Riemann hypothesis
for the Dedekind zeta functions of the Kummer fields $\mathbb{Q}(\zeta_k, a^{1/k})$, $k$
squarefree. These fields are in general non-abelian over $\mathbb{Q}$, so this hypothesis is not
covered by the Generalized Riemann Hypothesis for Dirichlet $L$-functions.

*References:*
- [Wikipedia](https://en.wikipedia.org/wiki/Artin%27s_conjecture_on_primitive_roots)
- [A85397](https://oeis.org/A85397)
- [LMS14](https://arxiv.org/pdf/1112.4816) Lenstra, H.W. et al. "Character sums for primitive root densities" _arXiv:1112.4816_ [math.NT] (2014).
- [Ho67] Hooley, C. "On Artin's conjecture." _Journal für die reine und angewandte Mathematik_ 225 (1967): 209-220.
-/

section


open GRH
open scoped Topology Nat

namespace ArtinPrimitiveRootsConjecture

/-- Let $S(a)$ be the set of primes such that $a$ is a primitive root modulo $p$. -/
abbrev S (a : ℤ) : Set ℕ :=
  {p : ℕ | p.Prime ∧ orderOf (a : ZMod p) = (p-1 : ℕ)}

/--
**Artin's Constant** is defined to be the product
$$\prod_{p\ \text{prime}} \left(1 - \frac{1}{p(p - 1)}\right)$$.
-/
noncomputable def ArtinConstant : ℝ :=
  ∏' p : Nat.Primes, (1 - 1 / (p * (p - 1)) : ℝ)

end ArtinPrimitiveRootsConjecture
