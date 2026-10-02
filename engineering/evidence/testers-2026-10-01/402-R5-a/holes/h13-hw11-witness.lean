import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h13».Context

open Filter

theorem witness : ∃ (n : ℕ), (67129 : ℕ) ≤ n ∧ n ≤ (80268 : ℕ) := ⟨67129, le_refl _, by norm_num⟩
