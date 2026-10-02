import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h11».Context

open Filter

theorem witness : ∃ (n : ℕ), (44505 : ℕ) ≤ n ∧ n ≤ (55208 : ℕ) := ⟨44505, le_refl _, by norm_num⟩
