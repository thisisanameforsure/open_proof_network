import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h18».Context

open Filter

theorem witness : ∃ (n : ℕ), (144755 : ℕ) ≤ n ∧ n ≤ (163941 : ℕ) := ⟨144755, le_refl _, by norm_num⟩
