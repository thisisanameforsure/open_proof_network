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
import Defs.Local

/-! Is the number of equilibria of n point charges bounded by a polynomial in n? A question left open by the disproof of the Maxwell conjecture (the registry's `maxwell_conjecture.variants.polynomial_bound`) — imported from google-deepmind/formal-conjectures (FormalConjectures/Arxiv/2607.27197/MaxwellConjecture.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); stated as the registry states it; the file's definitions are ported under defs/ (R12). -/

open scoped Gradient
open Arxiv.«2607.27197»

theorem Opn.maxwell_conjecture_polynomial_bound :
    ∃ C d : ℕ, ∀ (n : ℕ), 0 < n → ∀ (q : Fin n → ℝ) (a : Fin n → EuclideanSpace ℝ (Fin 3)),
      Function.Injective a → (∀ j, q j ≠ 0) →
      (∀ x ∈ equilibria q a, HasNondegenerateHessianAt (potential q a) x) →
      (equilibria q a).encard ≤ (C * n ^ d : ℕ) := by
  sorry
