open Filter

/-- The `n` the problem is about: `n ≥ 2`. (For `n = 1`, `σ(1) = 1`, so every iterate is `1` and the
limit is `1`; the question is only meaningful, and only intended, for `n > 1`.) -/
def domain (n : ℕ) : Prop := 2 ≤ n

instance : DecidablePred domain := fun n => by unfold domain; infer_instance

/-- `σ_k(n)` in the problem's own indexing: `σ_1(n) = σ(n)` and `σ_k(n) = σ(σ_{k-1}(n))`, i.e. the
`k`-fold iterate of the sum-of-divisors function (so `iter n 0 = n`). -/
def iter (n k : ℕ) : ℕ := (fun m : ℕ => ∑ d ∈ m.divisors, d)^[k] n

/-- For every `n ≥ 2`, `σ_k(n)^(1/k) → ∞` as `k → ∞`. -/
def conj : Prop :=
  ∀ n : ℕ, domain n →
    Tendsto (fun k : ℕ => ((iter n k : ℕ) : ℝ) ^ ((1 : ℝ) / (k : ℝ))) atTop atTop
