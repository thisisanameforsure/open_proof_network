open Nat

def domain (n : ℕ) : Prop := n ≥ 2

instance : DecidablePred domain := fun n => by unfold domain; infer_instance

def iter (n k : ℕ) : ℕ :=
  if k = 0 then 0
  else if k = 1 then divisorSigma 1 n
  else divisorSigma 1 (iter n (k - 1))

def conj : Prop := ∀ n, domain n → ∀ M : ℕ, ∃ K : ℕ, ∀ k ≥ K, iter n k > M ^ k
