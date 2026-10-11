import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h4».Context

open Filter

theorem witness : ∃ (n : ℕ), (2229 : ℕ) ≤ n ∧ n ≤ (4844 : ℕ) := ⟨2229, le_refl _, by norm_num⟩
