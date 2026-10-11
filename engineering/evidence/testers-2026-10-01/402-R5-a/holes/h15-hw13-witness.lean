import Mathlib
import Nodes.«erdos-402--h3-v2--h1--h1--h1--h1--h15».Context

open Filter

theorem witness : ∃ (n : ℕ), (94618 : ℕ) ≤ n ∧ n ≤ (110089 : ℕ) := ⟨94618, le_refl _, by norm_num⟩
