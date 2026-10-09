def domain (k : ℕ) : Prop := 1 < k
instance : DecidablePred domain := fun k => by unfold domain; infer_instance
def member (k n : ℕ) : Prop := ((n + k).factorial * (n + k).factorial) ∣ (n + n).factorial
instance (k : ℕ) : DecidablePred (member k) := fun n => by unfold member; infer_instance
def conj : Prop := ∀ k, domain k → Set.Infinite {n : ℕ | member k n}
