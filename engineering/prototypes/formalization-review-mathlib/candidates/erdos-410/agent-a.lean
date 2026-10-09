/-- The `n` the problem ranges over: positive integers (for `n = 0`, `σ 0 = 0` and the limit is `0`). -/
def domain (n : ℕ) : Prop := 1 ≤ n

instance : DecidablePred domain := fun n => by unfold domain; infer_instance

/-- `iter n k = σ_k(n)`, with `σ_1 = σ` (sum of divisors) and `σ_k = σ ∘ σ_{k-1}`;
the extra index `k = 0` is the identity, so `σ_1 n = σ (σ_0 n)`. -/
def iter (n : ℕ) : ℕ → ℕ
  | 0 => n
  | k + 1 => ArithmeticFunction.sigma 1 (iter n k)

/-- For every `n`, `σ_k(n)^(1/k) → ∞` as `k → ∞` (real arithmetic, tends to `atTop`). -/
def conj : Prop := ∀ n : ℕ, domain n →
  Filter.Tendsto (fun k : ℕ => ((iter n k : ℕ) : ℝ) ^ ((1 : ℝ) / (k : ℝ)))
    Filter.atTop Filter.atTop
