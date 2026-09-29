import Mathlib

open scoped ArithmeticFunction.omega

/-- One step of the tail recurrence: T_N = ω(N+1)/2 + T_{N+1}/2, where
T_N = ∑_{j ≥ 0} ω(N+1+j) / 2^(j+1). -/
theorem tail_step (N : ℕ)
    (hs : Summable fun j : ℕ => (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1)) :
    ∑' j : ℕ, (ω (N + 1 + j) : ℝ) / 2 ^ (j + 1)
      = (ω (N + 1) : ℝ) / 2 + (∑' j : ℕ, (ω (N + 2 + j) : ℝ) / 2 ^ (j + 1)) / 2 := by
  rw [hs.tsum_eq_zero_add, ← tsum_div_const]
  congr 1
  · simp
  · congr 1
    funext j
    rw [show N + 1 + (j + 1) = N + 2 + j by ring, pow_succ, div_div]
