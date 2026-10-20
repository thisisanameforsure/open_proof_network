lemma hadamard_inequality (n : ℕ) (A : Matrix (Fin n) (Fin n) ℝ) :
    A.det ^ 2 ≤ ∏ i : Fin n, ∑ j : Fin n, A i j ^ 2 := by
  set M := A * A.transpose with hM_def
  have hM_pos_semidef : Matrix.PosSemidef M := by
    constructor;
    · simp +decide [ hM_def, Matrix.IsHermitian, Matrix.transpose_mul ];
    · intro x
      have h_sum : ∑ i, ∑ j, x i * M i j * x j = ∑ k, (∑ i, x i * A i k) ^ 2 := by
        simp +zetaDelta at *;
        simp +decide [ Matrix.mul_apply, mul_assoc, mul_comm, mul_left_comm, sq, Finset.mul_sum _ _ _ ];
        exact Finset.sum_comm_cycle;
      simp_all +decide [ Finsupp.sum_fintype ];
      exact Finset.sum_nonneg fun _ _ => sq_nonneg _;
  obtain ⟨U, D, hU, hD⟩ : ∃ U : Matrix (Fin n) (Fin n) ℝ, ∃ D : Fin n → ℝ, U.transpose * U = 1 ∧ (∀ i, D i ≥ 0) ∧ M = U * Matrix.diagonal D * U.transpose := by
    have := Matrix.IsHermitian.spectral_theorem hM_pos_semidef.1;
    refine' ⟨ _, _, _, _, this ⟩;
    · have h := hM_pos_semidef.1.eigenvectorUnitary.2.1;
      simpa [Matrix.star_eq_conjTranspose] using h
    · exact fun i => hM_pos_semidef.eigenvalues_nonneg i;
  have h_det_M : Matrix.det M = ∏ i, D i := by
    apply_fun Matrix.det at hM_def ; simp_all +decide [ Matrix.det_mul, Matrix.det_diagonal ];
    have := congr_arg Matrix.det hU; norm_num at this; cases le_or_gt 0 ( U.det ) <;> nlinarith;
  have h_diag_M : ∀ i, M i i = ∑ j, U i j ^ 2 * D j := by
    simp +decide [ hD, Matrix.mul_apply, sq ];
    simp +decide [Matrix.diagonal, mul_comm, mul_left_comm];
  have h_am_gm : ∀ i, M i i ≥ ∏ j, D j ^ (U i j ^ 2) := by
    intro i;
    have := @Real.geom_mean_le_arith_mean;
    specialize this Finset.univ ( fun j => U i j ^ 2 ) ( fun j => D j ) ; simp_all +decide [ Matrix.mul_apply ];
    have h_sum_one : ∑ j, U i j ^ 2 = 1 := by
      simpa [ sq, Matrix.mul_apply ] using congr_arg ( fun m => m i i ) ( show U * U.transpose = 1 from by rw [ ← mul_eq_one_comm, hU ] );
    simpa [ h_sum_one ] using this ( fun j => sq_nonneg _ ) ( by rw [ h_sum_one ] ; norm_num );
  have h_prod_am_gm : ∏ i, M i i ≥ ∏ j, D j := by
    refine le_trans ?_ ( Finset.prod_le_prod ?_ fun i _ => h_am_gm i );
    · rw [ Finset.prod_comm, ← Finset.prod_congr rfl fun _ _ => Real.rpow_sum_of_nonneg ( hD.1 _ ) _ ];
      · simp_all +decide [← Matrix.ext_iff, sq];
        simp_all +decide [ Matrix.mul_apply, Matrix.one_apply ];
      · exact fun _ _ _ _ => sq_nonneg _;
    · exact fun i _ => Finset.prod_nonneg fun j _ => Real.rpow_nonneg ( hD.1 j ) _;
  simp_all +decide [ sq, Matrix.mul_apply ]