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

/-! Ported by hand from `FormalConjectures/Arxiv/math.0608009/DixmierConjecture.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0): the file's own definition `DixmierConjectureFor` with its `variable` lines, byte for byte, without the conjectures it states and their tests. The module syntax is stripped (`module`, `@[expose] public section` kept as a plain `section`) and its imports are made `import Mathlib` and `import Defs.AlgebraWeylAlgebra` (the library module that defines `WeylAlgebra`, as already ported on the live graph). Two changes beyond module syntax: the file's import of `FormalConjectures.Arxiv.«math.0608009».PoissonConjecture` is not carried, because the definition uses nothing from it; and its line `open JacobianConjecture` is left out, because `JacobianConjecture` is the namespace of another registry file (FormalConjectures/Wikipedia/JacobianConjecture.lean) that is not ported and the definition uses no name from it. -/

/-!
# The Dixmier Conjecture

*References:*
- [Dix68] [Sur les algèbres de Weyl](http://www.numdam.org/item/BSMF_1968__96__209_0/)
  by *Jacques Dixmier*, Bull. Soc. Math. France 96 (1968), 209–242. The conjecture is
  Problem 1 (for the first Weyl algebra).
- [BCW82] [The Jacobian conjecture: reduction of degree and formal expansion of the inverse](https://doi.org/10.1090/S0273-0979-1982-15032-7)
  by *Hyman Bass, Edwin H. Connell, David Wright*, Bull. Amer. Math. Soc. 7 (1982),
  287–330. Proves $DC_n \Longrightarrow JC_n$.
- [AvdE07] [arxiv/math.0608009](https://arxiv.org/abs/math/0608009)
  **On the equivalence of the Jacobian, Dixmier and Poisson Conjectures in any characteristic**
  by *Kossivi Adjamagbo, Arno van den Essen*. Published as *A proof of the equivalence of
  the Dixmier, Jacobian and Poisson conjectures*, Acta Math. Vietnam. 32 (2007), 205–214.
- [Tsu05] [Endomorphisms of Weyl algebra and p-curvatures](https://doi.org/10.18910/7472)
  by *Yoshifumi Tsuchimoto*, Osaka J. Math. 42 (2005), 435–452. Proves the stable
  equivalence $JC \Longleftrightarrow DC$ independently.
- [BKK07] [The Jacobian Conjecture is stably equivalent to the Dixmier Conjecture](https://doi.org/10.17323/1609-4514-2007-7-2-209-218)
  by *Alexei Belov-Kanel, Maxim Kontsevich*, Moscow Math. J. 7 (2007), 209–218. Independent
  proof of the stable equivalence.
- [Bav20] [The Jacobian Conjecture implies the Dixmier Problem](https://arxiv.org/abs/math/0512250)
  by *Vladimir Bavula*; published in Springer Proceedings in Mathematics & Statistics 317
  (2020). A third proof.
- [Alp26] [Counterexample to the Jacobian conjecture](https://x.com/__alpoge__/status/2079028340955197566)
  by *Levent Alpöge* (2026), disproving the Jacobian conjecture in dimension $3$
- [Lon26] [An Explicit Counterexample to the Rank-Two Poisson Conjecture](https://arxiv.org/abs/2608.23777)
  by *Christopher D. Long* (2026), disproving $PC_2$

The Dixmier Conjecture $DC_n$ asserts that, over a field `K` of characteristic zero, every
endomorphism of the `n`-th Weyl algebra $A_n(K)$ is an automorphism. For $n = 1$ this is
Problem 1 of [Dix68] and remains open.

By [BCW82], $DC_n \Longrightarrow JC_n$ (the Jacobian conjecture in dimension `n`) over a
fixed field `K`. By [AvdE07], Theorem 7, the chain
$$JC_{2n} \Longrightarrow PC_n \Longrightarrow DC_n \Longrightarrow JC_n$$
holds when each conjecture is quantified over all fields of characteristic zero
([AvdE07], Notations 5 and 7). Since the Jacobian conjecture fails in every dimension
$n ≥ 3$ [Alp26], the contrapositive of [BCW82] gives that $DC_n$ is **false for all
$n ≥ 3$**. $DC_1$ and $DC_2$ remain open. The chain only propagates falsity upwards, so the
failure of $PC_2$ [Lon26] does not settle $DC_2$.

The Weyl algebra $A_n(K)$ is `WeylAlgebra K (Fin n)`, with the $2n$ generators indexed by
`Fin n ⊕ Fin n` as in `FormalConjecturesForMathlib/Algebra/WeylAlgebra.lean`; the Poisson
side of the chain is stated in `PoissonConjecture.lean` in this directory.
-/

section

namespace Arxiv.«math.0608009»

variable {K : Type*} [Field K] [CharZero K]

variable (K) in
/-- The Dixmier Conjecture in dimension `n` ($DC_n$): every endomorphism of the `n`-th
Weyl algebra over `K` (a field of characteristic zero) is an automorphism. An algebra
endomorphism is an automorphism iff it is bijective. -/
def DixmierConjectureFor (n : ℕ) : Prop :=
  ∀ φ : WeylAlgebra K (Fin n) →ₐ[K] WeylAlgebra K (Fin n), Function.Bijective φ

end Arxiv.«math.0608009»
