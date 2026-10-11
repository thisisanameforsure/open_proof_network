open ArithmeticFunction
def member (n : ℕ) : Prop := sigma 1 n = sigma 1 (n + 1)
instance : DecidablePred member := fun n => by unfold member; infer_instance
def conj : Prop := Set.Infinite {n | member n}
