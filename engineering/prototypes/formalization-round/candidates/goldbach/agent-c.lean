/-- `p` is prime: at least 2, and no `d` with `2 ≤ d < p` divides it. -/
def IsPrime (p : Nat) : Prop := 2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0

instance : DecidablePred IsPrime := fun p =>
  inferInstanceAs (Decidable (2 ≤ p ∧ ∀ d, d < p → 2 ≤ d → p % d ≠ 0))

/-- If `n` is even and greater than 2, then `n = p + q` with `p` and `q` prime. -/
def claim (n : Nat) : Prop :=
  n % 2 = 0 → 2 < n → ∃ p, p < n + 1 ∧ IsPrime p ∧ IsPrime (n - p)

instance : DecidablePred claim := fun n =>
  inferInstanceAs (Decidable (n % 2 = 0 → 2 < n → ∃ p, p < n + 1 ∧ IsPrime p ∧ IsPrime (n - p)))
