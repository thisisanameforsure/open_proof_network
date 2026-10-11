open ArithmeticFunction Filter
def domain (n : ℕ) : Prop := True
instance : DecidablePred domain := fun n => by unfold domain; infer_instance
def iter (n k : ℕ) : ℕ := (sigma 1)^[k] n
def conj : Prop := ∀ n, domain n → Tendsto (fun k : ℕ ↦ (iter n k : ℝ) ^ (1 / (k : ℝ))) atTop atTop
