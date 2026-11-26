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

import Mathlib
import Defs.Local

/-! Conway's subprime Fibonacci sequences — imported from google-deepmind/formal-conjectures (FormalConjectures/Arxiv/1207.5099/SubprimeFibonacci.lean at d8d031d4998c78575159ccab9a7a9e95ce043883, Apache-2.0); stated as the registry states it, binders before the colon included; the names it takes from its file are ported under defs/ (R12). Curated by hand (curator B) and read by the lead before import (R13). -/

open Arxiv.«1207.5099»

theorem Opn.conjecture (x y : ℕ) (hx : 0 < x) (hy : 0 < y) :
    EventuallyPeriodic (x, y) := by
  sorry
