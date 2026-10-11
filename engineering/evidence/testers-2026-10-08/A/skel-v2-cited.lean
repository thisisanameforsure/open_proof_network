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
  -- annex: 315301b1f764421f86ce805ad2365a6ba8d8a64d428ba7d39e09e09c5c52382e
  have hall : (∀ k : ℕ, 0 < k → {n : ℕ | k * k ≤ n ∧ (n.choose k).minFac > n / k}.Finite) ∧
      (∃ K : ℕ, ∀ n k : ℕ, 0 < k → k * k ≤ n → (n.choose k).minFac > n / k → k ≤ K) ∧
      (∃ K : ℕ, ∀ n k : ℕ, 0 < k → 2 * k ≤ n → n < k * k → (n.choose k).minFac > k → k ≤ K) := by
    refine ⟨?_, ?_, ?_⟩
    · have h_fixed_k : ∀ k : ℕ, 0 < k →
          {n : ℕ | k * k ≤ n ∧ (n.choose k).minFac > n / k}.Finite := by
        sorry
      exact h_fixed_k
    · have h_large_n : ∃ K : ℕ, ∀ n k : ℕ, 0 < k → k * k ≤ n →
          (n.choose k).minFac > n / k → k ≤ K := by
        sorry
      exact h_large_n
    · have h_small_n : ∃ K : ℕ, ∀ n k : ℕ, 0 < k → 2 * k ≤ n → n < k * k →
          (n.choose k).minFac > k → k ≤ K := by
        sorry
      exact h_small_n
  obtain ⟨hF, ⟨KA, hA⟩, ⟨KB, hB⟩⟩ := hall
  have hT : ∀ k ∈ Finset.Icc 1 (max KA KB),
      ({n : ℕ | n < k * k} ∪ {n : ℕ | k * k ≤ n ∧ (n.choose k).minFac > n / k}).Finite := by
    intro k hk
    exact (Set.finite_lt_nat (k * k)).union (hF k (Finset.mem_Icc.1 hk).1)
  refine (Set.Finite.biUnion (Finset.Icc 1 (max KA KB)).finite_toSet
    (fun k hk => (hT k hk).image (fun n => (n, k)))).subset ?_
  rintro ⟨n, k⟩ ⟨hk, h2k, hmin⟩
  rw [Set.mem_iUnion₂]
  by_cases hnk : k * k ≤ n
  · have hkd : k ≤ n / k := (Nat.le_div_iff_mul_le hk).2 hnk
    have hmin' : (n.choose k).minFac > n / k := by rwa [max_eq_left hkd] at hmin
    have hbound : k ≤ max KA KB := le_trans (hA n k hk hnk hmin') (le_max_left _ _)
    exact ⟨k, Finset.mem_coe.2 (Finset.mem_Icc.2 ⟨hk, hbound⟩), n, Or.inr ⟨hnk, hmin'⟩, rfl⟩
  · have hlt : n < k * k := Nat.lt_of_not_le hnk
    have hdk : n / k ≤ k := le_of_lt ((Nat.div_lt_iff_lt_mul hk).2 hlt)
    have hmin' : (n.choose k).minFac > k := by rwa [max_eq_right hdk] at hmin
    have hbound : k ≤ max KA KB := le_trans (hB n k hk h2k hlt hmin') (le_max_right _ _)
    exact ⟨k, Finset.mem_coe.2 (Finset.mem_Icc.2 ⟨hk, hbound⟩), n, Or.inl hlt, rfl⟩
