def Prime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0
instance : DecidablePred Prime := fun p => by unfold Prime; infer_instance

def claim (n : Nat) : Prop := 2 ≤ n → (∃ p, p < n*n ∧ n*(n-1) < p ∧ Prime p) ∨ (∃ p, p < n*(n+1) ∧ n*n < p ∧ Prime p)
instance : DecidablePred claim := fun n => by unfold claim; infer_instance
