def IsPrime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0

instance : DecidablePred IsPrime := fun p => by unfold IsPrime; infer_instance

def claim (n : Nat) : Prop :=
  0 < n → ∃ p, p < (n + 1) * (n + 1) ∧ n * n < p ∧ IsPrime p

instance : DecidablePred claim := fun n => by unfold claim; infer_instance
