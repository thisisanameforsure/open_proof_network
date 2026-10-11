import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h19».Context

open Filter

theorem witness : ∃ (n : ℕ), (163942 : ℕ) ≤ n ∧ n ≤ (184361 : ℕ) := ⟨163942, le_refl _, by norm_num⟩
