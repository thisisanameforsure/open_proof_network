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
import Defs.Local

/-! Kurepa's conjecture, restricted to primes (the registry's `kurepa_conjecture.variants.prime`) — imported from google-deepmind/formal-conjectures (FormalConjectures/Paper/Kurepa.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); stated as the registry states it: for every prime p > 2, the left factorial !p = 0! + 1! + ⋯ + (p−1)! is not divisible by p. The registry proves this form equivalent to Kurepa's conjecture for all n > 2 (`kurepa_conjecture.prime_reduction`); the definition and its notation are ported under defs/ (R12). -/

open BigOperators Nat Finset
open Kurepa

theorem Opn.kurepa_conjecture_prime (p : ℕ) (h_p : 2 < p) :
    p.Prime → (!p : ℕ) % p ≠ 0 := by
  sorry
