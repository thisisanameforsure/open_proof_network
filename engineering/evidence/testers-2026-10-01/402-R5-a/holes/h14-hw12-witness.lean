import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h14».Context

open Filter

theorem witness : ∃ (n : ℕ), (80269 : ℕ) ≤ n ∧ n ≤ (94617 : ℕ) := ⟨80269, le_refl _, by norm_num⟩
