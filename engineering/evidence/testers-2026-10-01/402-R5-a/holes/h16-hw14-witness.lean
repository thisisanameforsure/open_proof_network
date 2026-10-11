import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h16».Context

open Filter

theorem witness : ∃ (n : ℕ), (110090 : ℕ) ≤ n ∧ n ≤ (126814 : ℕ) := ⟨110090, le_refl _, by norm_num⟩
