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
import Batteries.Data.Nat.Gcd

/-! Ported mechanically from `FormalConjecturesForMathlib/Data/Nat/Prime/Finset.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by gate/tools/wave.py (F14-T19): the module `FormalConjecturesForMathlib.Data.Nat.Prime.Finset`, lemmas included. The module syntax is stripped so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

section

/-- A Finset of numbers is coprime, or relatively prime, if its `gcd` is 1. -/
@[reducible] def Finset.Coprime (S : Finset ℕ) : Prop := S.gcd id = 1

theorem Finset.Coprime_pair_iff (S : Finset ℕ) (a b : ℕ) (h : S = {a, b}) :
    S.Coprime ↔ Nat.Coprime a b := by
  simp only [h, Finset.Coprime, Nat.Coprime, gcd_insert, gcd_singleton, normalize_eq]
  rfl
