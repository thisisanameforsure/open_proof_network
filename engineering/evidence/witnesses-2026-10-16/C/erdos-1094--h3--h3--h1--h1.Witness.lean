import Mathlib
import Nodes.«erdos-1094--h3--h3--h1--h1».Context
open scoped Nat

/-! The witness slot for a hole (D-29, F07-R6). Replace `sorry` with an instance
satisfying this statement's hypotheses; until then the node is blocked. -/

theorem witness : ∃ (ε : ℝ), (0 : ℝ) < ε := ⟨1, one_pos⟩
