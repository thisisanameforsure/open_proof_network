/-- `n` is a solution of `φ(n) = φ(n+1)`. -/
def member (n : ℕ) : Prop := Nat.totient n = Nat.totient (n + 1)

instance : DecidablePred member := fun n => by unfold member; infer_instance

/-- There are infinitely many solutions. -/
def conj : Prop := Set.Infinite {n : ℕ | member n}
