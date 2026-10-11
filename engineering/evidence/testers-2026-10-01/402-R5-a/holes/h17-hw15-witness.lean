import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h17».Context

open Filter

theorem witness : ∃ (n : ℕ), (126815 : ℕ) ≤ n ∧ n ≤ (144754 : ℕ) := ⟨126815, le_refl _, by norm_num⟩
