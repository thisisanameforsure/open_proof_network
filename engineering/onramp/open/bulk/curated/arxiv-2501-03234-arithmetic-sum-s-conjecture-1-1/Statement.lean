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

/-! An Arithmetic Sum Associated with the Classical Theta Function, Conjecture 1.1 — imported from google-deepmind/formal-conjectures (FormalConjectures/Arxiv/2501.03234/ArithmeticSumS.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); stated as the registry states it; the names it takes from its file are ported by hand under defs/ (R12). Curated by hand (cross-file class) and read by the curator before import (R13). -/

open Arxiv.«2501.03234»

theorem Opn.conjecture_1_1 (k : ℕ) (hprim : k.Prime) (hodd : Odd k) :
    0 < S k := by
  sorry
