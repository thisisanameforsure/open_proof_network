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

/-! Erdős problem 260: Let $a_1 < a_2 < \cdots$ be an increasing sequence such that $\frac{a_n}{n} \to \infty$. — imported from google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/260.lean at c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae, Apache-2.0); the registry states a yes/no question as `answer(sorry) ↔ P`; this states P, its affirmative reading (F11-Q24). Drafted by gate/tools/wave.py (F14-T11) and read by the curator before import (R13). -/

open Filter

theorem Opn.erdos_260 :
    ∀ a : ℕ → ℤ, ∀ s : ℝ,
                  StrictMono a →
                  Tendsto (fun n => (a n : ℝ ) / n ) atTop atTop →
                  HasSum (fun n => (a n : ℝ ) / 2 ^ a n) s → Irrational s := by
  sorry
