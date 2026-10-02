import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h12».Context

open Filter

theorem witness : ∃ (n : ℕ), (55209 : ℕ) ≤ n ∧ n ≤ (67128 : ℕ) := ⟨55209, le_refl _, by norm_num⟩
