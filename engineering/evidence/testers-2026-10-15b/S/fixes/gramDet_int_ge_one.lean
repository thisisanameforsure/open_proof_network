lemma gramDet_int_ge_one
    (r s : ℕ) (z : Fin r → (Fin s → ℤ))
    (hz : LinearIndependent ℤ z) :
    1 ≤ gramDet r s (fun k i => ((z k i : ℤ) : ℝ)) := by
  have h_real_indep : LinearIndependent ℝ (fun k => fun i => ((z k i : ℤ) : ℝ)) := by
    convert int_linearIndependent_implies_real r s z hz using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
  have h_pos_def : Matrix.PosDef (Matrix.of (fun i j => ∑ k, (z i k : ℝ) * (z j k : ℝ))) := by
    have h_pos_def : ∀ (v : Fin r → ℝ), v ≠ 0 → 0 < ∑ i, ∑ j, v i * v j * ∑ k, (z i k : ℝ) * (z j k : ℝ) := by
      intro v hv_ne_zero
      have h_pos_def : 0 < ∑ k, (∑ i, v i * (z i k : ℝ)) ^ 2 := by
        contrapose! hv_ne_zero
        generalize_proofs at *; (
        have h_zero : ∀ k, ∑ i, v i * (z i k : ℝ) = 0 := by
          exact fun k => sq_eq_zero_iff.mp ( le_antisymm ( le_trans ( Finset.single_le_sum ( fun a _ => sq_nonneg ( ∑ i, v i * ( z i a : ℝ ) ) ) ( Finset.mem_univ k ) ) hv_ne_zero ) ( sq_nonneg _ ) )
        generalize_proofs at *; (
        rw [ Fintype.linearIndependent_iff ] at h_real_indep
        generalize_proofs at *; (
        exact funext fun i => h_real_indep v ( by ext k; simpa [ mul_comm ] using h_zero k ) i)))
      generalize_proofs at *; (
      convert h_pos_def using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; simp +decide [ pow_two, mul_assoc, mul_comm, mul_left_comm, Finset.mul_sum _ _ _] ; ring_nf!;
      exact Finset.sum_comm_cycle)
    generalize_proofs at *; (
    constructor <;> norm_num [ Matrix.PosDef ];
    · ext i j; simp +decide [ mul_comm ] ;
    · intro x hx; specialize h_pos_def ( fun i => x i ) ; simp_all +decide [ Finsupp.sum_fintype, mul_assoc, mul_comm, mul_left_comm ] ;);
  have h_det_int : ∃ d : ℤ, Matrix.det (Matrix.of (fun i j => ∑ k, (z i k : ℝ) * (z j k : ℝ))) = d := by
    norm_num [ Matrix.det_apply' ];
    exact ⟨ ∑ x : Equiv.Perm ( Fin r ), Equiv.Perm.sign x * ∏ x_1 : Fin r, ∑ k : Fin s, z ( x x_1 ) k * z x_1 k, by push_cast; rfl ⟩;
  obtain ⟨ d, hd ⟩ := h_det_int; have := h_pos_def.det_pos; simp_all +decide [ gramDet ] ;
  exact_mod_cast this