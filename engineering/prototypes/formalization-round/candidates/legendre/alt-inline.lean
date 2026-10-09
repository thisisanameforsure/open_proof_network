def claim (n : Nat) : Prop := 1 ≤ n → ∃ p, p < (n+1)^2 ∧ n^2 < p ∧ 2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0
instance : DecidablePred claim := fun n => by unfold claim; infer_instance
