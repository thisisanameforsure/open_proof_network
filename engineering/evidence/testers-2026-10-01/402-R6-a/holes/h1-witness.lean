import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h2--h1».Context

open Filter

theorem witness : ∃ n : ℕ, 10 ≤ n ∧ n ≤ 228 := ⟨10, le_refl _, by norm_num⟩
