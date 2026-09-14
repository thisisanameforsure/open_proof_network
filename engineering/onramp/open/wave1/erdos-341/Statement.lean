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

/-! Erdős problem 341: Let $A=\{a_1 < \cdots < a_k\}$ be a finite set of integers and extend it to an infinite sequence $\overline{A}=\{a_1 < a_2 < \cdots \}$ by defining $a_{n+1}$ for $n \geq k$ to be th — imported from google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/341.lean at c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae, Apache-2.0); the registry states a yes/no question as `answer(sorry) ↔ P`; this states P, its affirmative reading (F11-Q24). Drafted by gate/tools/wave.py (F14-T11) and read by the curator before import (R13). -/

open Nat Set Filter
open scoped Topology

theorem Opn.erdos_341 :
    ∀ (a : ℕ → ℤ),
        (∀ᶠ n in atTop,
          IsLeast { x | a n < x ∧ x ∉ { a i + a j | (i ≤ n) (j ≤ n) } } (a (n + 1))) →
        let d := fun i ↦ a (i + 1) - a i
        ∃ p > 0, ∀ᶠ m in atTop, d (m + p) = d m := by
  sorry
