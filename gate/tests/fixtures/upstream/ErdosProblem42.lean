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

/-!
# A bounded-sum question

A shape-only stand-in for one registry statement, so the import path can be driven without a
checkout of the registry. It is deliberately already in D-3's shape: one theorem, one `sorry`
body.
-/

theorem erdos_42 : ∀ n : Nat, n ≤ n := sorry
