def Prime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0
instance : DecidablePred Prime := fun p => by unfold Prime; infer_instance

def claim (n : Nat) : Prop := 4 ≤ n → ∃ p, p ≤ n ∧ Prime p ∧ Prime (n - p)
instance : DecidablePred claim := fun n => by unfold claim; infer_instance
