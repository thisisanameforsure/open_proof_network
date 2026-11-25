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
import Defs.AlgebraMvPolynomialPoissonBracket

/-! Ported by hand from `FormalConjectures/Arxiv/math.0608009/PoissonConjecture.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0): the file's own definitions `IsPoissonEndomorphism` and `PoissonConjectureFor` with their `variable` lines, byte for byte, without the conjectures it states, their API lemmas and tests. The module syntax is stripped (`module`, `@[expose] public section` kept as a plain `section`) and its imports are made `import Mathlib` and `import Defs.AlgebraMvPolynomialPoissonBracket` (the library module that defines `MvPolynomial.poissonBracket`). One change beyond module syntax: the file's `open MvPolynomial JacobianConjecture` is `open MvPolynomial` here, because `JacobianConjecture` is the namespace of another registry file (FormalConjectures/Wikipedia/JacobianConjecture.lean) that is not ported, and neither definition uses a name from it. -/

/-!
# The Poisson Conjecture

*References:*
- [AvdE07] [arxiv/math.0608009](https://arxiv.org/abs/math/0608009)
  **On the equivalence of the Jacobian, Dixmier and Poisson Conjectures in any characteristic**
  by *Kossivi Adjamagbo, Arno van den Essen*. Published as *A proof of the equivalence of the
  Dixmier, Jacobian and Poisson conjectures*, Acta Math. Vietnam. 32 (2007), 205–214.
- [BCW82] [The Jacobian conjecture: reduction of degree and formal expansion of the inverse](https://doi.org/10.1090/S0273-0979-1982-15032-7)
  by *Hyman Bass, Edwin H. Connell, David Wright*, Bull. Amer. Math. Soc. 7 (1982), 287–330.
- [Alp26] [Counterexample to the Jacobian conjecture](https://x.com/__alpoge__/status/2079028340955197566)
  by *Levent Alpöge* (2026), disproving the Jacobian conjecture in dimension $3$
- [Lon26] [An Explicit Counterexample to the Rank-Two Poisson Conjecture](https://arxiv.org/abs/2608.23777)
  by *Christopher D. Long* (2026), disproving $PC_2$

The Poisson Conjecture $PC_n$ ([AvdE07], Notations 5) asserts that, over a field of
characteristic zero, every endomorphism of the `n`-th canonical Poisson algebra
$P_n(K)$ — the polynomial algebra $K[X_1, \dots, X_{2n}]$ equipped with the canonical
Poisson bracket — is an automorphism.

By [AvdE07], Theorem 7 (the "United Conjectures Theorem"), for every `n` there is a chain
of implications
$$JC_{2n} \Longrightarrow PC_n \Longrightarrow DC_n \Longrightarrow JC_n,$$
where $JC_n$ is the Jacobian Conjecture in dimension `n` and $DC_n$ the Dixmier Conjecture
for the `n`-th Weyl algebra (the implication $DC_n \Longrightarrow JC_n$ being classical [BCW82]).
Since the Jacobian conjecture was disproved in dimension $3$ [Alp26] — and hence in every
dimension $n ≥ 3$ by padding with identity coordinates — $PC_n$ is false for all $n ≥ 3$:
composing the counterexample's failure of $JC_3$ through $PC_3 \Longrightarrow DC_3 \Longrightarrow JC_3$ refutes
$PC_3$, and directly, the cotangent (symplectic) lift of the counterexample map
([AvdE07], Theorem 1 in reverse) is a non-invertible Poisson endomorphism of $P_3(K)$.
$PC_2$ is false as well, by the explicit rank-two counterexample of [Lon26]. Only $n = 1$
remains open.

Indexing note: we index the $2n$ variables of $P_n(K)$ by `Fin n ⊕ Fin n`, with
`Sum.inl i` playing the role of $X_i$ and `Sum.inr i` the role of $X_{i+n}$ of [AvdE07],
so that the canonical bracket reads $\{X_i, X_{i+n}\} = 1$; see
`MvPolynomial.poissonBracket`.
-/

section

namespace Arxiv.«math.0608009»

open MvPolynomial

variable {K : Type*} [Field K] [CharZero K]

/-- A `K`-algebra endomorphism `φ` of the polynomial algebra in $2n$ variables is an
endomorphism of the `n`-th canonical Poisson algebra $P_n(K)$ if it preserves the canonical
Poisson bracket. Following [AvdE07], Lemma 2, it is equivalent to require preservation on
the generators only, which is the form used here (the brackets of generators are constants,
so preserving and intertwining them agree). -/
def IsPoissonEndomorphism {n : ℕ}
    (φ : MvPolynomial (Fin n ⊕ Fin n) K →ₐ[K] MvPolynomial (Fin n ⊕ Fin n) K) : Prop :=
  ∀ v w, poissonBracket (φ (X v)) (φ (X w)) = poissonBracket (X v) (X w)

variable (K) in
/-- The Poisson Conjecture in dimension `n` ($PC_n$ in the notation of [AvdE07]): every
endomorphism of the `n`-th canonical Poisson algebra over `K` is an automorphism.
An endomorphism is an automorphism iff it is bijective, since the inverse of a bijective
algebra endomorphism preserving the Poisson bracket is again such. -/
def PoissonConjectureFor (n : ℕ) : Prop :=
  ∀ φ : MvPolynomial (Fin n ⊕ Fin n) K →ₐ[K] MvPolynomial (Fin n ⊕ Fin n) K,
    IsPoissonEndomorphism φ → Function.Bijective φ

end Arxiv.«math.0608009»
