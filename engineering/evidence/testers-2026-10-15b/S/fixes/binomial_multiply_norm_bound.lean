lemma binomial_multiply_norm_bound
    (s : ℕ) (M : ℝ) (u : Fin s → ℤ) (v : Fin s → ℤ) (ℓ : ℕ)
    (hu_range : ∀ i, 0 ≤ u i ∧ (u i : ℝ) ≤ M) :
    ∑ i : Fin s, ((Nat.choose (u i).toNat ℓ : ℤ) * v i : ℝ) ^ 2 ≤
      (M ^ ℓ / (Nat.factorial ℓ : ℝ)) ^ 2 * ∑ i : Fin s, ((v i : ℤ) : ℝ) ^ 2 := by
  have h_binom_bound : ∀ i, ((Nat.choose (u i).toNat ℓ) : ℝ) ≤ (M ^ ℓ / (Nat.factorial ℓ)) := by
    intro i
    have h_choose_bound : (Nat.choose (u i).toNat ℓ : ℝ) ≤ (↑(u i).toNat) ^ ℓ / (Nat.factorial ℓ) := by
      convert choose_le_pow_div_factorial ( Int.toNat ( u i ) ) ℓ using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
    refine le_trans h_choose_bound ?_;
    gcongr;
    exact le_trans ( mod_cast Int.toNat_of_nonneg ( hu_range i |>.1 ) |> le_of_eq ) ( hu_range i |>.2 );
  rw [ Finset.mul_sum _ _ _ ] ; exact Finset.sum_le_sum fun i _ => by simpa [ mul_pow ] using mul_le_mul_of_nonneg_right ( pow_le_pow_left₀ ( Nat.cast_nonneg _ ) ( h_binom_bound i ) 2 ) ( sq_nonneg _ ) ;