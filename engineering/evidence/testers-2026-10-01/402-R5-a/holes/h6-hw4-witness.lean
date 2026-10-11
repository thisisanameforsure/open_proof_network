import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h6».Context

open Filter

theorem witness : ∃ (n : ℕ), (8528 : ℕ) ≤ n ∧ n ≤ (13392 : ℕ) := ⟨8528, le_refl _, by norm_num⟩
