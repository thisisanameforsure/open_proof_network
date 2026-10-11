/-- `n` is a solution of `φ(n) = φ(n+1)`: a positive integer whose totient equals that of its
successor. (Positivity is stated for fidelity to "solutions" in the positive integers; it changes
nothing, since `φ 0 = 0 ≠ 1 = φ 1`.) -/
def member (n : ℕ) : Prop := 0 < n ∧ Nat.totient n = Nat.totient (n + 1)

instance : DecidablePred member := fun n => by unfold member; infer_instance

/-- There are infinitely many solutions to `φ(n) = φ(n+1)`. -/
def conj : Prop := Set.Infinite {n : ℕ | member n}
