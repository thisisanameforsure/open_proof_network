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

/-! Erdős problem 1094: For all $n\ge 2k$ the least prime factor of $\binom{n}{k}$ is $\le\max(n/k,k)$, with only finitely many exceptions. — imported from google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/1094.lean at c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae, Apache-2.0); stated as the registry states it. Drafted by gate/tools/wave.py (F14-T11) and read by the curator before import (R13). -/

open scoped Nat

theorem Opn.erdos_1094 :
    {(n, k) : ℕ × ℕ | 0 < k ∧ 2 * k ≤ n ∧ (n.choose k).minFac > max (n / k) k}.Finite := by
  sorry
