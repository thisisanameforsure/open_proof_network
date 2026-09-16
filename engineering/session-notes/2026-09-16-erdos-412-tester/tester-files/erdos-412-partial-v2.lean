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

/-! Erdős problem 412: Let $σ_1(n)=σ(n)$, the sum of divisors function, and $σ_k(n) = σ(σ_{k-1}(n))$. — imported from google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/412.lean at c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae, Apache-2.0); the registry states a yes/no question as `answer(sorry) ↔ P`; this states P, its affirmative reading (F11-Q24). Drafted by gate/tools/wave.py (F14-T11) and read by the curator before import (R13). -/

open ArithmeticFunction.sigma

theorem Opn.erdos_412 :
    ∀ᵉ (m ≥ 2) (n ≥ 2), ∃ i j, (σ 1)^[i] m = (σ 1)^[j] n := by
  -- annex: 0000000000000000000000000000000000000000000000000000000000000000
  -- HOLE (the open core, in its weakest useful form): for composite k the
  -- trajectories of k and k+1 meet.  The prime case is discharged below.
  have composite : ∀ k, 2 ≤ k → ¬ k.Prime →
      ∃ i j, (σ 1)^[i] k = (σ 1)^[j] (k + 1) := sorry
  -- ASSEMBLY.
  -- (1) A prime p has σ p = p + 1, so p's trajectory enters (p+1)'s in one step.
  have consec : ∀ k, 2 ≤ k → ∃ i j, (σ 1)^[i] k = (σ 1)^[j] (k + 1) := by
    intro k hk
    by_cases hp : k.Prime
    · refine ⟨1, 0, ?_⟩
      rw [Function.iterate_one, Function.iterate_zero_apply,
        ArithmeticFunction.sigma_one_apply, hp.divisors, Finset.sum_pair hp.one_lt.ne]
      exact Nat.add_comm 1 k
    · exact composite k hk hp
  -- (2) "x and y merge" is symmetric and transitive along the forward orbits.
  have symm : ∀ x y : ℕ, (∃ i j, (σ 1)^[i] x = (σ 1)^[j] y) →
      ∃ i j, (σ 1)^[i] y = (σ 1)^[j] x := by
    rintro x y ⟨a, b, h⟩
    exact ⟨b, a, h.symm⟩
  have trans : ∀ x y z : ℕ, (∃ i j, (σ 1)^[i] x = (σ 1)^[j] y) →
      (∃ i j, (σ 1)^[i] y = (σ 1)^[j] z) → ∃ i j, (σ 1)^[i] x = (σ 1)^[j] z := by
    rintro x y z ⟨a, b, hab⟩ ⟨c, d, hcd⟩
    refine ⟨c + a, b + d, ?_⟩
    rw [Function.iterate_add_apply, hab, ← Function.iterate_add_apply, Nat.add_comm c b,
      Function.iterate_add_apply, hcd, ← Function.iterate_add_apply]
  -- (3) Induction from 2 upwards: every m ≥ 2 merges with 2.
  have up : ∀ m, 2 ≤ m → ∃ i j, (σ 1)^[i] m = (σ 1)^[j] 2 := by
    intro m hm
    induction m, hm using Nat.le_induction with
    | base => exact ⟨0, 0, rfl⟩
    | succ k hk ih => exact trans (k + 1) k 2 (symm k (k + 1) (consec k hk)) ih
  -- (4) Two numbers that both merge with 2 merge with each other.
  intro m hm n hn
  exact trans m 2 n (up m hm) (symm n 2 (up n hn))
