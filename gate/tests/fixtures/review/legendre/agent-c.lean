/-- `p` is prime: at least 2, and no `d` with `2 ≤ d < p` divides it. -/
def IsPrime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0

instance : DecidablePred IsPrime := fun p =>
  inferInstanceAs (Decidable (2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0))

/-- If `n` is positive, some prime `p` satisfies `n^2 < p < (n+1)^2`. -/
def claim (n : Nat) : Prop :=
  0 < n → ∃ p, p < (n + 1) ^ 2 ∧ n ^ 2 < p ∧ IsPrime p

instance : DecidablePred claim := fun n =>
  inferInstanceAs (Decidable (0 < n → ∃ p, p < (n + 1) ^ 2 ∧ n ^ 2 < p ∧ IsPrime p))
