open ArithmeticFunction Filter
def domain (n : ℕ) : Prop := 2 ≤ n
instance : DecidablePred domain := fun n => by unfold domain; infer_instance
def iter (n k : ℕ) : ℕ := (sigma 1)^[k] n
def conj : Prop := ∀ n, domain n → ∀ M : ℝ, ∃ K : ℕ, ∀ k ≥ K, M ≤ (iter n k : ℝ) ^ (1 / (k : ℝ))
