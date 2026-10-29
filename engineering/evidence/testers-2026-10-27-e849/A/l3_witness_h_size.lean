-- hole: h_size

import Mathlib

open Nat

theorem witness : ∃ (a : ℕ) (n : ℕ) (k : ℕ), (1 : ℕ) ≤ k ∧ (2 : ℕ) * k ≤ n ∧ n.choose k = a :=
  ⟨2, 2, 1, by norm_num, by norm_num, by decide⟩
