open scoped Nat
def member (n : ℕ) : Prop := Nat.totient n = Nat.totient (n + 1)
instance : DecidablePred member := fun n => by unfold member; infer_instance
def conj : Prop := ∀ N : ℕ, ∃ n, N < n ∧ member n
