def Prime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0
instance : DecidablePred Prime := fun p => by unfold Prime; infer_instance

def claim (n : Nat) : Prop := 1 ≤ n → ∃ p, p < (n+1)^2 ∧ (n^2 < p → Prime p)
instance : DecidablePred claim := fun n => by unfold claim; infer_instance
