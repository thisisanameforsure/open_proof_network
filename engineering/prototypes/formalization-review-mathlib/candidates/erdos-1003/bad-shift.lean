open scoped Nat
def member (n : ℕ) : Prop := φ n = φ (n + 2)
instance : DecidablePred member := fun n => by unfold member; infer_instance
def conj : Prop := Set.Infinite {n | member n}
