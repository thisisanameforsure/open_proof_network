def IsPrime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0

instance : DecidablePred IsPrime := fun p => by unfold IsPrime; infer_instance

def claim (n : Nat) : Prop :=
  (n % 2 = 0 ∧ 2 < n) → ∃ p, p ≤ n ∧ ∃ q, q ≤ n ∧ IsPrime p ∧ IsPrime q ∧ p + q = n

instance : DecidablePred claim := fun n => by unfold claim; infer_instance
