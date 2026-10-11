import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h7».Context

open Filter

theorem witness : ∃ (n : ℕ), (13393 : ℕ) ≤ n ∧ n ≤ (19388 : ℕ) := ⟨13393, le_refl _, by norm_num⟩
