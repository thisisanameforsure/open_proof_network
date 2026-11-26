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
import Defs.DataZModFp

/-! Ported from `FormalConjectures/GreensOpenProblems/31.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by hand (curator C), in the form gate/tools/wave.py (F14-T19) gives a problem file: the file's own definitions, without the conjectures it states and their tests (the `category API` and `category test` lemmas included), and without `green_31.lower.answer`, `green_31.upper.answer`, `green_31.variants.lower_eventually.answer` and `green_31.variants.upper_eventually.answer`, whose registry body is a placeholder term rather than a definition (the adapted statement binds its own function instead). The module syntax is stripped so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

/-!
# Ben Green's Open Problem 31

Write $F(N)$ for the largest Sidon subset of $[N]$.
Improve, at least for infinitely many $N$, the bounds $N^{1/2} + O(1) \le F(N) \le N^{1/2} + N^{1/4} + O(1)$.

Note: the upper bound was improved to $N^{1/2} + 0.98183 N^{1/4} + O(1)$ in [CHO25], and then to
$N^{1/2} + 0.94349\ldots N^{1/4} + O(1)$ in [HZ26].

Related to Erdős Problem 30.

*References:*
- [Gr24] [Ben Green's Open Problem 31](https://people.maths.ox.ac.uk/greenbj/papers/open-problems.pdf#section.7 Problem 31)
- [Gr01] Green, Ben. "The number of squares and $ B_h [g] $ sets."
  Acta Arithmetica 100.4 (2001): 365-390.
- [BFR23] Balogh, József, Zoltán Füredi, and Souktik Roy. "An upper bound on the size of Sidon sets."
  The American Mathematical Monthly 130.5 (2023): 437-445.
- [CHO25] Carter, Daniel, Zach Hunter, and Kevin O’Bryant. "On the diameter of finite Sidon sets."
  Acta Mathematica Hungarica 175.1 (2025): 108-126.
- [HZ26] Hou, Jianfeng, and Hongbin Zhao. "An Improved Upper Bound for Finite Sidon Sets via
  Vector-Valued Smoothing." [arXiv:2607.01169](https://arxiv.org/abs/2607.01169) (2026).
- [ET41] Erdos, Paul, and Pál Turán. "On a problem of Sidon in additive number theory, and on some
  related problems." J. London Math. Soc 16.4 (1941): 212-215.
- [Li69] Lindström, Bernt. “A remark on B4-Sequences.” Journal of Combinatorial Theory,
  Series A 7 (1969): 276-277.
- [CLZ01] Cohen, G.D., Litsyn, S., & Zémor, G. (2001). Binary B2-Sequences : A New Upper Bound.
  J. Comb. Theory A, 94, 152-155.
- [BS85] Babai, László, and Vera T. Sós. "Sidon sets in groups and induced subgraphs of Cayley
  graphs." European Journal of Combinatorics 6.2 (1985): 101-114.
  [doi:10.1016/S0195-6698(85)80001-9](https://doi.org/10.1016/S0195-6698%2885%2980001-9)
-/

section

namespace Green31

open Filter

/-- Let $F(N)$ be the largest Sidon subset of $[N]$. -/
noncomputable def F (N : ℕ) : ℝ := Finset.maxSidonSubsetCard (Finset.Icc 1 N)

/--
A subset $S$ of an abelian group is a Sidon set of the first kind in the sense of Babai and Sós
[BS85] if $a + b = c + d$ with $a, b, c, d \in S$ implies $|\{a, b, c, d\}| \le 2$.

Unlike `IsSidon`, this allows $a + a = b + b$ with $a \ne b$.
-/
def IsGroupSidon {G : Type*} [AddCommGroup G] (S : Set G) : Prop :=
  ∀ ⦃a b c d : G⦄, a ∈ S → b ∈ S → c ∈ S → d ∈ S → a + b = c + d →
    (a = c ∧ b = d) ∨ (a = d ∧ b = c) ∨ (a = b ∧ c = d)

/--
A set of binary vectors is Sidon if its pairwise sums, taken coordinatewise in `ℕ`, determine the
unordered pair of summands.
-/
def IsBinarySidon {n : ℕ} (S : Set (𝔽₂ n)) : Prop :=
  ∀ ⦃a b c d : 𝔽₂ n⦄, a ∈ S → b ∈ S → c ∈ S → d ∈ S →
    (fun i ↦ (a i).val + (b i).val) = (fun i ↦ (c i).val + (d i).val) →
      (a = c ∧ b = d) ∨ (a = d ∧ b = c)

end Green31
