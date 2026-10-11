open Nat

/-- The `k` the problem is about: `k ≥ 2`. -/
def domain (k : ℕ) : Prop := 2 ≤ k

instance : DecidablePred domain := fun k => by unfold domain; infer_instance

/-- For this `k` and `n`, `((n+k)!)² ∣ (2n)!`. -/
def member (k n : ℕ) : Prop := ((n + k)! ) ^ 2 ∣ (2 * n)!

instance (k : ℕ) : DecidablePred (member k) := fun n => by unfold member; infer_instance

/-- For every `k ≥ 2`, the divisibility `((n+k)!)² ∣ (2n)!` holds for infinitely many `n`. -/
def conj : Prop := ∀ k : ℕ, domain k → Set.Infinite {n : ℕ | member k n}
