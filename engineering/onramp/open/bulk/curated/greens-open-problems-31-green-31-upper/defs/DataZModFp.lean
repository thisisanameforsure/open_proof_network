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

/-! Ported from `FormalConjecturesForMathlib/Data/ZMod/Fp.lean` at registry commit d8d031d4998c78575159ccab9a7a9e95ce043883 (google-deepmind/formal-conjectures, Apache-2.0) by hand (curator C), in the form gate/tools/wave.py (F14-T19) gives a library module: the module `FormalConjecturesForMathlib.Data.ZMod.Fp`, lemmas included. The module syntax is stripped so the gate elaborates it under `import Mathlib`; nothing else is changed. -/

section

/-!
# Notation for finite field vector spaces

This file defines the notation `𝔽 p n` for the vector space `Fin n → ZMod p`
over the finite field of order `p`, and provides standard abbreviations for
small primes.
-/

/-- `𝔽 p n` is the vector space `(Z/pZ)^n`. When `p` is prime, this is $\mathbb{F}_p^n$. -/
abbrev 𝔽 (p n : ℕ) := Fin n → ZMod p

/-- `𝔽₂ n` is the vector space $\mathbb{F}_2^n$. -/
abbrev 𝔽₂ (n : ℕ) := 𝔽 2 n

/-- `𝔽₃ n` is the vector space $\mathbb{F}_3^n$. -/
abbrev 𝔽₃ (n : ℕ) := 𝔽 3 n

/-- `𝔽₅ n` is the vector space $\mathbb{F}_5^n$. -/
abbrev 𝔽₅ (n : ℕ) := 𝔽 5 n

/-- `𝔽₇ n` is the vector space $\mathbb{F}_7^n$. -/
abbrev 𝔽₇ (n : ℕ) := 𝔽 7 n
