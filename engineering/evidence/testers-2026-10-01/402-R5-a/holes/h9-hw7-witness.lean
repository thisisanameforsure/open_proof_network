import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h9».Context

open Filter

theorem witness : ∃ (n : ℕ), (26541 : ℕ) ≤ n ∧ n ≤ (34904 : ℕ) := ⟨26541, le_refl _, by norm_num⟩
