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
  -- annex: 7a8596acf85bd1718e83f30d4c82cf0dc8c2a2889bd4accc374c8dad8f9bf85b
  -- Write x ~ y for "the forward σ-orbits of x and y meet", the relation this
  -- statement asserts holds for every pair of integers ≥ 2.
  --
  -- HOLE (the open core, in its weakest useful form): a descent step, needed
  -- only for those m that no smaller starting point flows into.
  have descent : ∀ m, 3 ≤ m → (¬ ∃ x, 2 ≤ x ∧ x < m ∧ ∃ k, (σ 1)^[k] x = m) →
      ∃ m', 2 ≤ m' ∧ m' < m ∧ ∃ i j, (σ 1)^[i] m = (σ 1)^[j] m' := sorry
  -- ASSEMBLY.
  -- (1) ~ is symmetric and transitive, because the orbits are deterministic:
  -- from σ^a x = σ^b y and σ^c y = σ^d z, σ^(c+a) x = σ^c (σ^b y) = σ^b (σ^c y) = σ^(b+d) z.
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
  -- (2) every m ≥ 2 satisfies m ~ 2, by strong induction.  If some smaller
  -- x ≥ 2 flows into m then m ~ x outright (this covers every m of the form
  -- σ p = p + 1 for p prime, and every other value of σ below m); otherwise
  -- the hole supplies a smaller partner.
  have up : ∀ m, 2 ≤ m → ∃ i j, (σ 1)^[i] m = (σ 1)^[j] 2 := by
    intro m
    induction m using Nat.strong_induction_on with
    | _ m ih =>
      intro hm
      rcases Nat.lt_or_ge m 3 with hlt | h3
      · have hm2 : m = 2 := by omega
        subst hm2
        exact ⟨0, 0, rfl⟩
      · by_cases hx : ∃ x, 2 ≤ x ∧ x < m ∧ ∃ k, (σ 1)^[k] x = m
        · obtain ⟨x, hx2, hxm, k, hxeq⟩ := hx
          refine trans m x 2 ⟨0, k, ?_⟩ (ih x hxm hx2)
          rw [Function.iterate_zero_apply, hxeq]
        · obtain ⟨m', hm'2, hm'lt, hmerge⟩ := descent m h3 hx
          exact trans m m' 2 hmerge (ih m' hm'lt hm'2)
  -- (3) m ~ 2 and n ~ 2 give m ~ n.
  intro m hm n hn
  exact trans m 2 n (up m hm) (symm n 2 (up n hn))
