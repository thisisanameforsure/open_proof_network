open scoped Nat
/-- The live root, verbatim (Formal Conjectures), and the format's names wrapped around it. -/
def original : Prop := Set.Infinite {n | φ n = φ (n + 1)}
def member (n : ℕ) : Prop := φ n = φ (n + 1)
instance : DecidablePred member := fun n => by unfold member; infer_instance
def conj : Prop := Set.Infinite {n | member n}
theorem port : conj ↔ original := Iff.rfl
