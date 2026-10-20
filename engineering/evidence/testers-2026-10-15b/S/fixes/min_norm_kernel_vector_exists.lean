lemma min_norm_kernel_vector_exists
    (r s : ℕ) (hr : 2 ≤ r) (hs : s = 2 * r)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_strict : StrictMono u) (hw_pos : ∀ i, 0 < w i)
    (V : Submodule ℝ (Fin s → ℝ)) (hV_dim : Module.finrank ℝ V < r) :
    ∃ x : Fin s → ℤ,
      (∀ j : ℕ, j < r → ∑ i, (x i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧
      (fun i : Fin s => (x i : ℝ)) ∉ V ∧
      (∀ y : Fin s → ℤ,
        (∀ j : ℕ, j < r → ∑ i, (y i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) →
        (fun i : Fin s => (y i : ℝ)) ∉ V →
        int_sq_norm s x ≤ int_sq_norm s y) := by
  obtain ⟨x, hx_kernel, hx_not_in_V⟩ : ∃ x : Fin s → ℤ, (∀ j < r, ∑ i, (x i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧ (fun i => (x i : ℝ)) ∉ V := by
    obtain ⟨ v, hv ⟩ := integer_kernel_has_r_independent_vectors r hr s hs u w hu_strict hw_pos;
    contrapose! hV_dim;
    have hV_dim : Module.finrank ℝ (Submodule.span ℝ (Set.range (fun k : Fin r => (fun i => ((v k i : ℤ) : ℝ))))) ≤ Module.finrank ℝ V := by
      exact Submodule.finrank_mono <| Submodule.span_le.mpr <| Set.range_subset_iff.mpr fun k => hV_dim _ <| hv.1 k;
    rw [ finrank_span_eq_card ] at hV_dim <;> aesop;
  have h_finite : Set.Finite {y : Fin s → ℤ | (∀ j < r, ∑ i, (y i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧ (fun i => (y i : ℝ)) ∉ V ∧ int_sq_norm s y ≤ int_sq_norm s x} := by
    have h_finite : Set.Finite {y : Fin s → ℤ | int_sq_norm s y ≤ int_sq_norm s x} := by
      convert finite_integer_vectors_bounded_norm s ( int_sq_norm s x ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
      norm_num [ ← int_sq_norm_eq_real_sq_norm ];
    exact h_finite.subset fun y hy => hy.2.2;
  obtain ⟨y, hy⟩ : ∃ y ∈ {y : Fin s → ℤ | (∀ j < r, ∑ i, (y i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧ (fun i => (y i : ℝ)) ∉ V ∧ int_sq_norm s y ≤ int_sq_norm s x}, ∀ z ∈ {y : Fin s → ℤ | (∀ j < r, ∑ i, (y i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧ (fun i => (y i : ℝ)) ∉ V ∧ int_sq_norm s y ≤ int_sq_norm s x}, int_sq_norm s y ≤ int_sq_norm s z := by
    apply_rules [ Set.exists_min_image ];
    exact ⟨ x, hx_kernel, hx_not_in_V, le_rfl ⟩;
  exact ⟨ y, hy.1.1, hy.1.2.1, fun z hz₁ hz₂ => if hz₃ : int_sq_norm s z ≤ int_sq_norm s x then hy.2 z ⟨ hz₁, hz₂, hz₃ ⟩ else by linarith [ hy.1.2.2 ] ⟩