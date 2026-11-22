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

/-! Ported verbatim from `FormalConjecturesForMathlib/Data/Nat/Prime/Composite.lean` at registry
commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0):
the registry's `Nat.Composite`, which `green_58` states its conclusion with (F14-R12). -/

abbrev Nat.Composite (n : ℕ) : Prop := 1 < n ∧ ¬n.Prime
