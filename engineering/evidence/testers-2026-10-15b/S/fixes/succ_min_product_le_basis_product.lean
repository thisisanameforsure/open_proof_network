lemma succ_min_product_le_basis_product
    (r s : ℕ)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (v : Fin r → (Fin s → ℤ))
    (hv_succ : ∀ k : Fin r, ∀ x : Fin s → ℤ,
      (∀ j : ℕ, j < r → ∑ i, (x i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) →
      (fun i : Fin s => (x i : ℝ)) ∉
        Submodule.span ℝ ((fun j : Fin r => fun i : Fin s => (v j i : ℝ)) ''
          { j | j.val < k.val }) →
      ∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2 ≤ ∑ i : Fin s, ((x i : ℤ) : ℝ) ^ 2)
    (y : Fin r → (Fin s → ℤ))
    (hy_kernel : ∀ (k : Fin r) (j : ℕ), j < r →
      ∑ i, (y k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0)
    (hy_indep : LinearIndependent ℝ (fun k : Fin r => (fun i : Fin s => ((y k i : ℤ) : ℝ))))
    (hy_sorted : Monotone (fun k : Fin r => ∑ i : Fin s, ((y k i : ℤ) : ℝ) ^ 2)) :
    ∏ k : Fin r, (∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2) ≤
      ∏ k : Fin r, (∑ i : Fin s, ((y k i : ℤ) : ℝ) ^ 2) := by
  apply Finset.prod_le_prod;
  · exact fun _ _ => Finset.sum_nonneg fun _ _ => sq_nonneg _;
  · intro k hk
    obtain ⟨j, hj⟩ : ∃ j ≤ k, (fun i => (y j i : ℝ)) ∉ Submodule.span ℝ (Set.image (fun l : Fin r => (fun i => ((v l i : ℝ))) ) {l | l.val < k.val}) := by
      by_contra h_contra;
      have h_subspace : Module.finrank ℝ (Submodule.span ℝ (Set.image (fun l : Fin r => (fun i => ((y l i : ℝ))) ) (Finset.Iic k))) ≤ k.val := by
        have h_subspace : Submodule.span ℝ (Set.image (fun l : Fin r => (fun i => ((y l i : ℝ))) ) (Finset.Iic k)) ≤ Submodule.span ℝ (Set.image (fun l : Fin r => (fun i => ((v l i : ℝ))) ) {l | l.val < k.val}) := by
          exact Submodule.span_le.mpr ( Set.image_subset_iff.mpr fun l hl => by aesop );
        refine' le_trans ( Submodule.finrank_mono h_subspace ) _;
        convert finrank_span_image_lt s r k ( fun l i => ( v l i : ℝ ) ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
      rw [ Set.image_eq_range ] at h_subspace;
      rw [ finrank_span_eq_card ] at h_subspace <;> norm_num at *;
      first
        | exact hy_indep.comp _ Subtype.coe_injective
        | (convert hy_indep.comp _ Subtype.coe_injective using 1)
        | (convert hy_indep.comp _ Subtype.coe_injective)
    exact le_trans ( hv_succ k ( y j ) ( hy_kernel j ) hj.2 ) ( hy_sorted hj.1 )