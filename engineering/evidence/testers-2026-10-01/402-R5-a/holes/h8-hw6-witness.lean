import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h8».Context

open Filter

theorem witness : ∃ (n : ℕ), (19389 : ℕ) ≤ n ∧ n ≤ (26540 : ℕ) := ⟨19389, le_refl _, by norm_num⟩
