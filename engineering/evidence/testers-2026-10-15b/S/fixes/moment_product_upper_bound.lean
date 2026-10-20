lemma moment_product_upper_bound (r : ℕ) (hr : 2 ≤ r) (M : ℝ) (hM : 0 ≤ M) :
    ∏ j ∈ Finset.range r, (M ^ j / (Nat.factorial j : ℝ)) ≤
    (64 * M / (r : ℝ)) ^ (r * (r - 1) / 2) := by
  have hr0 : (0 : ℝ) < (r : ℝ) := by exact_mod_cast (show 0 < r by omega)
  have hP : 0 < ((r : ℝ) / 64) ^ (r * (r - 1) / 2) := pow_pos (div_pos hr0 (by norm_num)) _
  rw [Finset.prod_div_distrib, Finset.prod_pow_eq_pow_sum, Finset.sum_range_id]
  rw [show (64 * M / (r : ℝ)) ^ (r * (r - 1) / 2) = M ^ (r * (r - 1) / 2) / ((r : ℝ) / 64) ^ (r * (r - 1) / 2) by
    rw [div_pow, div_pow, mul_pow]; first | (field_simp; done) | (field_simp; ring)]
  exact div_le_div_of_nonneg_left (pow_nonneg hM _) hP (factorial_product_lower_bound r hr)