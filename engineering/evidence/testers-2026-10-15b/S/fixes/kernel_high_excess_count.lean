lemma kernel_high_excess_count
    (r s e : ℕ) (hs : s = 2 * r) (he : e ≤ r)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_strict : StrictMono u) (hw_pos : ∀ i, 0 < w i)
    (t : ℕ) (v : Fin t → (Fin s → ℤ))
    (hv : ∀ (k : Fin t) (j : ℕ), j < r + e →
      ∑ i, (v k i : ℝ) * (w i : ℝ) * (u i : ℝ) ^ j = 0)
    (hv_indep : LinearIndependent ℝ (fun k : Fin t => fun i : Fin s => (v k i : ℝ))) :
    t ≤ r - e := by
  have h_rank : Matrix.rank (Matrix.of (fun (j : Fin (r + e)) (i : Fin s) => (w i : ℝ) * ((u i : ℝ)) ^ j.val)) = r + e := by
    have h_vandermonde_indep : LinearIndependent ℝ (fun j : Fin (r + e) => fun i : Fin s => (w i : ℝ) * ((u i : ℝ)) ^ j.val) := by
      refine' Fintype.linearIndependent_iff.2 _;
      intro g hg i
      have h_poly : ∀ i_1 : Fin s, ∑ j : Fin (r + e), g j * ((u i_1 : ℝ)) ^ (j : ℕ) = 0 := by
        intro i_1; replace hg := congr_fun hg i_1; simp_all +decide ;
        convert congr_arg ( fun x : ℝ => x / ( w i_1 : ℝ ) ) hg using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) <;> norm_num [ Finset.sum_div _ _ _, mul_assoc, mul_comm, mul_left_comm, ne_of_gt ( hw_pos i_1 ) ];
        exact Finset.sum_congr rfl fun _ _ => by rw [ mul_div_assoc, mul_div_cancel_right₀ _ ( Nat.cast_ne_zero.mpr <| ne_of_gt <| hw_pos i_1 ) ] ;
      have h_poly_zero : ∑ j : Fin (r + e), g j • (Polynomial.monomial j.val (1 : ℝ)) = 0 := by
        refine' Polynomial.eq_of_degree_sub_lt_of_eval_finset_eq _ _ _;
        exact Finset.image ( fun i : Fin s => ( u i : ℝ ) ) Finset.univ;
        · rw [ Finset.card_image_of_injective _ fun i j hij => hu_strict.injective <| by simpa using hij ] ; norm_num [ Polynomial.degree_lt_iff_coeff_zero ];
          simp +decide [ Polynomial.coeff_monomial ];
          exact fun m hm => Finset.sum_eq_zero fun i hi => if_neg <| by linarith [ Fin.is_lt i ] ;
        · simp_all +decide [ Polynomial.eval_finset_sum ];
      replace h_poly_zero := congr_arg ( fun p => p.coeff i ) h_poly_zero ; simp_all +decide [ Polynomial.coeff_monomial ];
      simp_all +decide [ Fin.val_inj ];
    rw [Matrix.rank_eq_finrank_span_row]
    exact (finrank_span_eq_card h_vandermonde_indep).trans (Fintype.card_fin _)
  have h_ker_dim : Module.finrank ℝ (LinearMap.ker (Matrix.mulVecLin (Matrix.of (fun (j : Fin (r + e)) (i : Fin s) => (w i : ℝ) * ((u i : ℝ)) ^ j.val)))) = s - (r + e) := by
    have := LinearMap.finrank_range_add_finrank_ker ( Matrix.mulVecLin ( Matrix.of ( fun ( j : Fin ( r + e ) ) ( i : Fin s ) => ( w i : ℝ ) * ( u i : ℝ ) ^ j.val ) ) );
    have hr' : Module.finrank ℝ (LinearMap.range (Matrix.mulVecLin (Matrix.of (fun (j : Fin (r + e)) (i : Fin s) => (w i : ℝ) * ((u i : ℝ)) ^ j.val)))) = r + e := h_rank
    rw [hr', Module.finrank_fin_fun] at this
    omega
  have h_span_ker : Submodule.span ℝ (Set.range (fun k : Fin t => (fun i : Fin s => ((v k i : ℤ) : ℝ)))) ≤ LinearMap.ker (Matrix.mulVecLin (Matrix.of (fun (j : Fin (r + e)) (i : Fin s) => (w i : ℝ) * ((u i : ℝ)) ^ j.val))) := by
    rw [ Submodule.span_le ];
    rintro _ ⟨ k, rfl ⟩ ; ext j; simp +decide [ Matrix.mulVec, dotProduct, mul_comm, mul_left_comm ] ;
    simpa only [ mul_assoc, mul_comm, mul_left_comm ] using hv k j ( Fin.is_lt j );
  have := Submodule.finrank_mono h_span_ker;
  rw [ finrank_span_eq_card ] at this <;> norm_num [ hv_indep ] at * ; omega