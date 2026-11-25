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

/-! Ported by hand from `FormalConjectures/Arxiv/1207.5099/SubprimeFibonacci.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by curator B: the file's own definitions, without the conjectures it states and their tests. The module syntax is stripped (`module`, `public import`, `@[expose] public section`) so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

/-!
# Conway's subprime Fibonacci sequences

A subprime Fibonacci sequence starts from two positive integers. Each new term is the sum of the
previous two terms if that sum is prime; if the sum is composite, it is divided once by its least
prime factor. This file formalizes the no-infinite-chains component of the conjecture: every such
sequence eventually enters a cycle. It does not assert that the seven known loops are complete or
unique.

*References:*
- R. K. Guy, T. Khovanova, and J. Salazar,
  ["Conway's subprime Fibonacci sequences"](https://arxiv.org/abs/1207.5099),
  *Mathematics Magazine* **87** (2014), no. 5, 323–337.
- [A214897](https://oeis.org/A214897), Conway's subprime Fibonacci sequence: cycle lengths.
-/

section

namespace Arxiv.«1207.5099»

/--
Conway's subprime function leaves a prime unchanged and divides a composite number once by its
least prime factor. It is extended by the identity on $0$ and $1$.
-/
def subprimePart (n : ℕ) : ℕ :=
  if n < 2 then n else if n.Prime then n else n / n.minFac

/--
One step of the subprime Fibonacci recurrence on a pair of consecutive terms. The second entry
becomes the first, and the subprime part of the sum becomes the second.
-/
def step (state : ℕ × ℕ) : ℕ × ℕ :=
  (state.2, subprimePart (state.1 + state.2))

/-- A pair state is eventually periodic if some positive iterate fixes a later state. -/
def EventuallyPeriodic (initial : ℕ × ℕ) : Prop :=
  ∃ preperiod period : ℕ, 0 < period ∧
    Function.IsPeriodicPt step period ((step^[preperiod]) initial)

end Arxiv.«1207.5099»
