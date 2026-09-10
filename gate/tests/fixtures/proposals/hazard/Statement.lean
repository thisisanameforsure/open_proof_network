import Nodes.«hazard».Context

/-! An unacknowledged ℕ subtraction: F02's nat-sub checker fires (D-4 step 6). -/

theorem OpnAdv.pred_lt : ∀ n : Nat, 0 < n → n - 1 < n := by
  sorry
