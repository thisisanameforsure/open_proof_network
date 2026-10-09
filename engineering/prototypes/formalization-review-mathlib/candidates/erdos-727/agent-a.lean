/-- The `k` the problem ranges over: `k ≥ 2`. -/
def domain (k : ℕ) : Prop := 2 ≤ k

instance : DecidablePred domain := fun k => by unfold domain; infer_instance

/-- `((n+k)!)² ∣ (2n)!`. -/
def member (k n : ℕ) : Prop := ((n + k).factorial) ^ 2 ∣ (2 * n).factorial

instance (k : ℕ) : DecidablePred (member k) := fun n => by unfold member; infer_instance

/-- For every `k ≥ 2`, the divisibility holds for infinitely many `n`. -/
def conj : Prop := ∀ k : ℕ, domain k → Set.Infinite {n : ℕ | member k n}
