-- hole: h_fixed_k

import Mathlib

open scoped Nat

theorem witness : ∃ k : ℕ, 0 < k := ⟨1, Nat.one_pos⟩
