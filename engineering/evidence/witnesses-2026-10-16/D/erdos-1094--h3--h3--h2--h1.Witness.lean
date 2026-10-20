import Mathlib
import Nodes.«erdos-1094--h3--h3--h2--h1».Context
open scoped Nat

/-! The witness slot for a hole (D-29, F07-R6). Replace `sorry` with an instance
satisfying this statement's hypotheses; until then the node is blocked. -/

theorem witness : ∃ (C : ℕ) (δ : ℝ), (0 : ℝ) < δ := ⟨0, 1, one_pos⟩
