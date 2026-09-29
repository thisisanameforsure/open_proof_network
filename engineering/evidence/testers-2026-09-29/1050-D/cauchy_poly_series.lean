import Mathlib

theorem cauchy_poly_series (n : ℕ) (c : ℕ → ℝ) (x V : ℝ)
    (hV : HasSum (fun k : ℕ => x ^ k / ((2 : ℝ) ^ k - 1)) V) :
    HasSum (fun m : ℕ => (∑ j ∈ Finset.range (n + 1), c j / ((2 : ℝ) ^ (m - j) - 1)) * x ^ m)
      ((∑ j ∈ Finset.range (n + 1), c j * x ^ j) * V) := by
  have hj : ∀ j ∈ Finset.range (n + 1),
      HasSum (fun m : ℕ => c j / ((2 : ℝ) ^ (m - j) - 1) * x ^ m) (c j * x ^ j * V) := by
    intro j _
    refine (hasSum_nat_add_iff' j).mp ?_
    have h0 : ∑ i ∈ Finset.range j, c j / ((2 : ℝ) ^ (i - j) - 1) * x ^ i = 0 := by
      apply Finset.sum_eq_zero
      intro i hi
      rw [Finset.mem_range] at hi
      rw [show i - j = 0 by omega]
      simp
    rw [h0, sub_zero]
    have hfun : (fun m : ℕ => c j / ((2 : ℝ) ^ (m + j - j) - 1) * x ^ (m + j)) =
        fun m : ℕ => c j * x ^ j * (x ^ m / ((2 : ℝ) ^ m - 1)) := by
      funext m
      rw [show m + j - j = m by omega, pow_add]
      ring
    rw [hfun]
    exact hV.mul_left (c j * x ^ j)
  have h := hasSum_sum hj
  rw [← Finset.sum_mul] at h
  convert h using 1
  funext m
  rw [Finset.sum_mul]
