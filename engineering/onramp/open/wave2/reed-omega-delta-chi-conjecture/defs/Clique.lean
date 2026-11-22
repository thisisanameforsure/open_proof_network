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

/-! Ported verbatim from `FormalConjecturesForMathlib/Combinatorics/SimpleGraph/Clique.lean` at
registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures,
Apache-2.0): the clique number `reed_omega_delta_chi_conjecture` uses (F14-R12). -/

open Finset

namespace SimpleGraph

/-- Infinite graphs: definitions for clique number so that the clique number of a graph
with unbounded clique size is `∞` rather than 0.
-/
noncomputable
def ecliqueNum {V : Type} (G : SimpleGraph V) : ℕ∞ := ⨆ (s : Finset V) (_ : G.IsClique s), #s

end SimpleGraph
