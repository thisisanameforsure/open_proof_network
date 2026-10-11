import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h5».Context

open Filter

theorem witness : ∃ (n : ℕ), (4845 : ℕ) ≤ n ∧ n ≤ (8527 : ℕ) := ⟨4845, le_refl _, by norm_num⟩
