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

/-! Erdős problem 257: Let $A\subseteq\mathbb{N}$ be an infinite set. — imported from google-deepmind/formal-conjectures (FormalConjectures/ErdosProblems/257.lean at c7f31d5fd3d2ca3d69979f2d213eb9b58fe956ae, Apache-2.0); the registry states a yes/no question as `answer(sorry) ↔ P`; this states P, its affirmative reading (F11-Q24). Drafted by gate/tools/wave.py (F14-T11) and read by the curator before import (R13). -/

theorem Opn.erdos_257 :
    ∀ (A : Set ℕ), A.Infinite →
    Irrational (∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1)) := by
  -- annex: 91f974f5322a5af6fbb42be7d529c58fe7cd39798e06cb7ddd0cdd1f2975fbd6
  -- approach: greedy walk; a representation of a rational is greedy (bookkeeping), and the open core is that a greedy set summing to a rational is finite (expected false: the walk for 1/2 runs past 10^8)
  -- licence: CC-BY-4.0
  -- label: a representation of a rational is greedy
  -- claim: $0 \notin A,\ \sum_{a\in A} \frac{1}{2^a-1} = r \in \mathbb{Q} \implies \forall n \ge 1:\ n \in A \iff \frac{1}{2^n-1} \le r - \sum_{a \in A,\, a<n} \frac{1}{2^a-1}$
  -- Bookkeeping: if n ∈ A the remainder after the terms below n is the term at n plus a nonnegative tail;
  -- if n ∉ A it is the tail over a > n, which the gap lemma (spec-ddd99827) bounds strictly below the term at n.
  -- Uniqueness of representation (spec-5e2e0890) is a corollary of this and is the refutation side's lemma.
  have h_greedy : ∀ (r : ℚ) (A : Set ℕ), 0 ∉ A →
      ∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1) = r →
      ∀ n : ℕ, 1 ≤ n → (n ∈ A ↔
        (1 : ℝ) / (2 ^ n - 1) ≤ r - ∑' a : ↥(A ∩ Set.Iio n), (1 : ℝ) / (2 ^ a.1 - 1)) := sorry
  -- label: the greedy walk for a rational stalls (open core)
  -- claim: $0 \notin G,\ G \text{ greedy for } r \in \mathbb{Q},\ \sum_{a\in G} \frac{1}{2^a-1} = r \implies G \text{ finite}$
  -- The open core of Erdős 257. Expected FALSE: Kovač (erdosproblems.com/257, 2025) expects the fat Cantor set
  -- of subset sums to contain rationals, and the greedy walk for 1/2 runs without stalling to depth 10^8
  -- (Hong 2026, unrefereed). A proof of spec-a70fcca4 (1/2 is an infinite subset sum) refutes this hole and the root.
  -- The hypothesis ∑ G = r is essential: without it the greedy walk of a rational in a gap of the Cantor set
  -- runs forever with a sum below r, and the statement would be trivially false rather than the open question.
  have h_core : ∀ (r : ℚ) (G : Set ℕ), 0 ∉ G →
      (∀ n : ℕ, 1 ≤ n → (n ∈ G ↔
        (1 : ℝ) / (2 ^ n - 1) ≤ r - ∑' a : ↥(G ∩ Set.Iio n), (1 : ℝ) / (2 ^ a.1 - 1))) →
      ∑' n : G, (1 : ℝ) / (2 ^ n.1 - 1) = r → G.Finite := sorry
  intro A hA
  rintro ⟨r, hr⟩
  have h0 : ∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1) = ∑' n : ↥(A \ {0}), (1 : ℝ) / (2 ^ n.1 - 1) := by
    have e1 : ∑' n : A, (1 : ℝ) / (2 ^ n.1 - 1)
        = ∑' n : ℕ, A.indicator (fun m : ℕ => (1 : ℝ) / (2 ^ m - 1)) n :=
      tsum_subtype A (fun m : ℕ => (1 : ℝ) / (2 ^ m - 1))
    have e2 : ∑' n : ↥(A \ {0}), (1 : ℝ) / (2 ^ n.1 - 1)
        = ∑' n : ℕ, (A \ {0}).indicator (fun m : ℕ => (1 : ℝ) / (2 ^ m - 1)) n :=
      tsum_subtype (A \ {0}) (fun m : ℕ => (1 : ℝ) / (2 ^ m - 1))
    rw [e1, e2]
    congr 1
    funext x
    by_cases hx : x = 0
    · subst hx; simp [Set.indicator]
    · have hmem : x ∈ A \ {0} ↔ x ∈ A := by simp [hx]
      by_cases hxA : x ∈ A
      · rw [Set.indicator_of_mem hxA, Set.indicator_of_mem (hmem.mpr hxA)]
      · rw [Set.indicator_of_notMem hxA, Set.indicator_of_notMem (fun h => hxA (hmem.mp h))]
  have hA' : (A \ {0}).Infinite := hA.sdiff (Set.finite_singleton 0)
  have hsum : ∑' n : ↥(A \ {0}), (1 : ℝ) / (2 ^ n.1 - 1) = r := by rw [← h0, hr]
  have hgr := h_greedy r (A \ {0}) (by simp) hsum
  exact hA' (h_core r (A \ {0}) (by simp) hgr hsum)
