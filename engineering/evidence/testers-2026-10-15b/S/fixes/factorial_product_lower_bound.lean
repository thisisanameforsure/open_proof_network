lemma factorial_product_lower_bound (r : ℕ) (hr : 2 ≤ r) :
    ((r : ℝ) / 64) ^ (r * (r - 1) / 2) ≤
    ∏ j ∈ Finset.range r, (Nat.factorial j : ℝ) := by
  induction' r with r ih <;> norm_num [ Finset.prod_range_succ ] at *;
  by_cases hr : r ≤ 64;
  · interval_cases r <;> norm_num [ Nat.factorial_succ, Finset.prod_range_succ ]
    all_goals first
      | (rw [show (2080 : ℕ) = 32 * 65 by norm_num, pow_mul]
         exact le_trans (pow_le_pow_left₀ (by norm_num) (show ((65 : ℝ) / 64) ^ 32 ≤ 3 by norm_num) 65) (by norm_num))
      | exact le_trans (pow_le_one₀ (by norm_num) (by norm_num)) (by norm_num)
  · -- For the inductive step, we can use the fact that $r! \geq \left(\frac{r}{e}\right)^r$.
    have h_factorial_bound : (r.factorial : ℝ) ≥ (r / Real.exp 1) ^ r := by
      rw [ div_pow, ge_iff_le, div_le_iff₀ ] <;> norm_cast <;> norm_num [ Nat.factorial_pos ];
      · rw [ ← div_le_iff₀' ( by positivity ) ] ; rw [ Real.exp_eq_exp_ℝ ] ; norm_num [ NormedSpace.exp_eq_tsum_div ] ; exact Summable.le_tsum ( show Summable _ from Real.summable_pow_div_factorial _ ) r ( fun _ _ => by positivity ) ;
      · positivity;
    suffices h_div : ((r + 1) / r : ℝ) ^ (r * (r - 1) / 2) * ((r + 1) / 64 : ℝ) ^ r ≤ (r / Real.exp 1) ^ r by
      refine le_trans ?_ ( mul_le_mul ( ih <| by linarith ) h_factorial_bound ?_ ?_ ) <;> try positivity;
      convert mul_le_mul_of_nonneg_left h_div ( show ( 0 :ℝ ) ≤ ( r / 64 ) ^ ( r * ( r - 1 ) / 2 ) by positivity ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
      rw [ ← mul_assoc, ← mul_pow ];
      rw [ show ( r + 1 ) * r / 2 = r * ( r - 1 ) / 2 + r by exact Nat.div_eq_of_eq_mul_left zero_lt_two <| by nlinarith [ Nat.sub_add_cancel ( by linarith : 1 ≤ r ), Nat.div_mul_cancel ( show 2 ∣ r * ( r - 1 ) from even_iff_two_dvd.mp <| Nat.even_mul_pred_self _ ) ] ] ; rw [ pow_add ] ; ring_nf;
      norm_num [ sq, mul_assoc, ne_of_gt ( by linarith : 0 < r ) ];
    suffices h_root : ((r + 1) / r : ℝ) ^ ((r - 1) / 2 : ℝ) * ((r + 1) / 64 : ℝ) ≤ (r / Real.exp 1) by
      convert pow_le_pow_left₀ ( by positivity ) h_root r using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; norm_num [ mul_pow, ← Real.rpow_natCast, ← Real.rpow_mul ( by positivity : 0 ≤ ( r + 1 : ℝ ) / r ) ] ; ring_nf ; norm_num [ Nat.cast_sub ( show 1 ≤ r by linarith ) ] ; ring_nf;
      exact Or.inl ( by rw [ ← Real.rpow_natCast ] ; rw [ Nat.cast_div ( show 2 ∣ r * ( r - 1 ) from even_iff_two_dvd.mp ( Nat.even_mul_pred_self _ ) ) ( by positivity ) ] ; cases r <;> norm_num ; ring_nf ) ;
    have h_exp_bound : ((r + 1) / r : ℝ) ^ ((r - 1) / 2 : ℝ) ≤ Real.exp (1 / 2) := by
      rw [ Real.rpow_def_of_pos ( by exact div_pos ( by positivity ) ( by norm_cast; linarith ) ) ];
      norm_num +zetaDelta at *;
      exact le_trans ( mul_le_mul_of_nonneg_right ( Real.log_le_sub_one_of_pos ( by positivity ) ) ( by linarith [ show ( r : ℝ ) ≥ 65 by norm_cast ] ) ) ( by nlinarith [ show ( r : ℝ ) ≥ 65 by norm_cast, div_mul_cancel₀ ( ( r : ℝ ) + 1 ) ( by positivity : ( r : ℝ ) ≠ 0 ) ] );
    refine le_trans ( mul_le_mul_of_nonneg_right h_exp_bound <| by positivity ) ?_;
    rw [ le_div_iff₀ ( Real.exp_pos _ ) ];
    have := Real.exp_one_lt_d9.le ; norm_num1 at * ; rw [ show ( 1 : ℝ ) = 1 / 2 + 1 / 2 by norm_num, Real.exp_add ] at * ; norm_num at *;
    nlinarith [ Real.add_one_le_exp ( 1 / 2 ), show ( r : ℝ ) ≥ 65 by norm_cast, mul_le_mul_of_nonneg_left ( show ( r : ℝ ) ≥ 65 by norm_cast ) ( Real.exp_nonneg ( 1 / 2 ) ) ]