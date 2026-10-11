import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h3».Context

open Filter

theorem witness : ∃ (n : ℕ), (681 : ℕ) ≤ n ∧ n ≤ (2228 : ℕ) := ⟨681, le_refl _, by norm_num⟩
