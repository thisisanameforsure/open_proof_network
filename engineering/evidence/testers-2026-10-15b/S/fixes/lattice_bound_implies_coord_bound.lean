lemma lattice_bound_implies_coord_bound (r : ℕ) (hr : 2 ≤ r) (M W : ℝ)
    (hM : 0 ≤ M) (hW : 0 ≤ W) :
    (∏ j ∈ Finset.range r, (M ^ j / (Nat.factorial j : ℝ))) ^ 4 *
    (2 : ℝ) ^ (r * (r - 1)) * (2 * (r : ℝ)) ^ r * W ^ (2 * r) ≤
    ((256 * M / (r : ℝ)) ^ (r - 1 : ℕ) * W) ^ (2 * r) := by
  have h1 : (∏ j ∈ Finset.range r, (M ^ j / (Nat.factorial j : ℝ))) ^ 4 ≤ (64 * M / r) ^ (2 * r * (r - 1)) := by
    convert pow_le_pow_left₀ ( Finset.prod_nonneg fun _ _ => by positivity ) ( moment_product_upper_bound r hr M hM ) 4 using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; ring_nf;
    rw [ show r * ( r - 1 ) * 2 = r * ( r - 1 ) / 2 * 4 by linarith [ Nat.div_mul_cancel ( show 2 ∣ r * ( r - 1 ) from even_iff_two_dvd.mp ( Nat.even_mul_pred_self _ ) ) ] ];
  have h2 : (2 * r : ℝ) ^ r ≤ 8 ^ (r * (r - 1)) := by
    convert pow_le_pow_left₀ ( by positivity ) ( two_mul_r_le_eight_pow r hr ) r using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; ring
  have h3 : (2 : ℝ) ^ (r * (r - 1)) * (2 * r) ^ r ≤ 4 ^ (2 * r * (r - 1)) := by
    convert mul_le_mul_of_nonneg_left h2 ( pow_nonneg zero_le_two ( r * ( r - 1 ) ) ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; ring_nf;
    norm_num [ pow_mul', ← mul_pow ];
  convert mul_le_mul_of_nonneg_right ( mul_le_mul h1 h3 ( by positivity ) ( by positivity ) ) ( by positivity : 0 ≤ W ^ ( 2 * r ) ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; ring;
  rw [ show ( 256 * M / r : ℝ ) = ( 64 * M / r ) * 4 by ring ] ; rw [ mul_pow ] ; ring_nf;
  norm_num [ mul_assoc, ← mul_pow ]