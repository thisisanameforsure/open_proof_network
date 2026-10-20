lemma binomial_multiply_moment
    (s : ℕ) (u : Fin s → ℤ) (w : Fin s → ℕ) (v : Fin s → ℤ)
    (hu_nonneg : ∀ i, 0 ≤ u i) (e : ℕ) :
    ∀ r : ℕ,
    (∀ t : ℕ, t < r + e → ∑ i, (v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ t = 0) →
    (∑ i, (v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ (r + e) ≠ 0) →
    ∑ i, ((Nat.choose (u i).toNat e : ℤ) * v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0 := by
  induction' e with e ih;
  · aesop;
  · intro r hr₁ hr₂;
    have h_identity : ∑ i, (Nat.choose (u i).toNat (e + 1) * v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r = (1 / (e + 1 : ℝ)) * (∑ i, (Nat.choose (u i).toNat e * v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ (r + 1)) - (e / (e + 1 : ℝ)) * (∑ i, (Nat.choose (u i).toNat e * v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r) := by
      have h_identity : ∀ i, (Nat.choose (u i).toNat (e + 1) : ℝ) = (Nat.choose (u i).toNat e : ℝ) * ((u i : ℝ) - e) / (e + 1) := by
        intro i; rw [ eq_div_iff ] <;> norm_cast ;
        cases h : u i <;> simp_all +decide [ Nat.choose_succ_right_eq ];
        · exact Classical.or_iff_not_imp_right.2 fun h' => by rw [ Nat.cast_sub ( le_of_not_gt fun h'' => h' <| Nat.choose_eq_zero_of_lt h'' ) ] ;
        · linarith [ hu_nonneg i, Int.negSucc_lt_zero ‹_› ];
      rw [ Finset.mul_sum _ _ _, Finset.mul_sum _ _ _ ] ; rw [ ← Finset.sum_sub_distrib ] ; congr ; ext i ; rw [ h_identity i ] ; ring;
    have h_ind : ∑ i, (Nat.choose (u i).toNat e * v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ (r + 1) ≠ 0 := by
      apply ih (r + 1);
      · exact fun t ht => hr₁ t ( by linarith );
      · convert hr₂ using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; ring_nf;
    have h_ind : ∑ i, (Nat.choose (u i).toNat e * v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r = 0 := by
      convert kernel_binomial_multiply s u w v hu_nonneg e ( r + 1 ) ( fun t ht => hr₁ t ( by linarith ) ) r ( by linarith ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
    simp_all +decide [ Nat.cast_add_one_ne_zero ]