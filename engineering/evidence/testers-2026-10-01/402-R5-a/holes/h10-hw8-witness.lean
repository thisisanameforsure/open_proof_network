import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h10».Context

open Filter

theorem witness : ∃ (n : ℕ), (34905 : ℕ) ≤ n ∧ n ≤ (44504 : ℕ) := ⟨34905, le_refl _, by norm_num⟩
