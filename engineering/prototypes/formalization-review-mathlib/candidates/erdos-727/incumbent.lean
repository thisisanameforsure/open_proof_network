open scoped Nat
def original : Prop := ∀ k ≥ 2, Set.Infinite {n : ℕ | (Nat.factorial (n + k)) ^ 2 ∣ Nat.factorial (2 * n)}
def domain (k : ℕ) : Prop := k ≥ 2
instance : DecidablePred domain := fun k => by unfold domain; infer_instance
def member (k n : ℕ) : Prop := (Nat.factorial (n + k)) ^ 2 ∣ Nat.factorial (2 * n)
instance (k : ℕ) : DecidablePred (member k) := fun n => by unfold member; infer_instance
def conj : Prop := ∀ k, domain k → Set.Infinite {n : ℕ | member k n}
theorem port : conj ↔ original := Iff.rfl
