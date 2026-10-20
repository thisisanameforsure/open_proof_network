import Mathlib

theorem h1_test : Summable (fun m : ℕ => (1 : ℝ) / (2 ^ m - 1)) := by
  have hgeom : Summable (fun m : ℕ => (2 : ℝ) * (1 / 2) ^ m) :=
    (summable_geometric_of_lt_one (by norm_num) (by norm_num)).mul_left 2
  refine Summable.of_nonneg_of_le (fun m => ?_) (fun m => ?_) hgeom
  · apply div_nonneg zero_le_one
    have : (1 : ℝ) ≤ 2 ^ m := one_le_pow₀ (by norm_num)
    linarith
  · rcases Nat.eq_zero_or_pos m with rfl | hm
    · simp
    · have h2m : (2 : ℝ) ≤ 2 ^ m := by
        calc (2 : ℝ) = 2 ^ 1 := by norm_num
          _ ≤ 2 ^ m := pow_le_pow_right₀ (by norm_num) hm
      have hpos : (0 : ℝ) < 2 ^ m - 1 := by linarith
      rw [one_div_pow, mul_one_div, div_le_div_iff₀ hpos (by positivity)]
      linarith
