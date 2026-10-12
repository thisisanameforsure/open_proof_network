/-- `p` is prime: at least 2, and no `d` with `2 ≤ d < p` divides it. -/
def IsPrime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0

instance : DecidablePred IsPrime := fun p =>
  inferInstanceAs (Decidable (2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0))

/-- If `n > 1`, some prime lies strictly between `n(n-1)` and `n^2`, and some prime
lies strictly between `n^2` and `n(n+1)`. -/
def claim (n : Nat) : Prop :=
  1 < n →
    (∃ p, p < n ^ 2 ∧ n * (n - 1) < p ∧ IsPrime p) ∧
    (∃ q, q < n * (n + 1) ∧ n ^ 2 < q ∧ IsPrime q)

instance : DecidablePred claim := fun n =>
  inferInstanceAs (Decidable (1 < n →
    (∃ p, p < n ^ 2 ∧ n * (n - 1) < p ∧ IsPrime p) ∧
    (∃ q, q < n * (n + 1) ∧ n ^ 2 < q ∧ IsPrime q)))
