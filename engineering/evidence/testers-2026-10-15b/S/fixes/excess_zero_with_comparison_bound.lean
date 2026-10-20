lemma excess_zero_with_comparison_bound
    (r : ℕ) (hr : 2 ≤ r)
    (s : ℕ) (hs : s = 2 * r)
    (M : ℝ) (hM : (s : ℝ) - 1 ≤ M)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_range : ∀ i, 0 ≤ u i ∧ (u i : ℝ) ≤ M)
    (hu_strict : StrictMono u)
    (hw_pos : ∀ i, 0 < w i)
    (v : Fin r → (Fin s → ℤ))
    (hv_kernel : ∀ (k : Fin r) (j : ℕ), j < r →
      ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0)
    (hv_indep : LinearIndependent ℝ (fun k : Fin r => (fun i : Fin s => ((v k i : ℤ) : ℝ))))
    (hv_mono : Monotone (fun k : Fin r => ∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2))
    (hv_succ : ∀ k : Fin r, ∀ x : Fin s → ℤ,
      (∀ j : ℕ, j < r → ∑ i, (x i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) →
      (fun i : Fin s => (x i : ℝ)) ∉
        Submodule.span ℝ ((fun j : Fin r => fun i : Fin s => (v j i : ℝ)) ''
          { j | j.val < k.val }) →
      ∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2 ≤ ∑ i : Fin s, ((x i : ℤ) : ℝ) ^ 2) :
    ∃ m : Fin r,
      (∑ i, (v m i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0) ∧
      (∑ i : Fin s, ((v m i : ℤ) : ℝ) ^ 2) ^ r ≤
        (∏ j ∈ Finset.range r, ((M : ℝ) ^ j / (Nat.factorial j : ℝ))) ^ 2 *
        ∏ k : Fin r, (∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2) := by
  obtain ⟨m, hm⟩ : ∃ m : Fin r, ∑ i, (v m i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0 ∧ ∀ k : Fin r, k.val < m.val → ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r = 0 := by
    obtain ⟨m, hm⟩ : ∃ m : Fin r, ∑ i, (v m i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0 := by
      apply excess_zero_among_independent r hr s hs u w hu_strict hw_pos v hv_kernel hv_indep;
    obtain ⟨m, hm⟩ : ∃ m : Fin r, ∑ i, (v m i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0 ∧ ∀ k : Fin r, k.val < m.val → ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r = 0 := by
      have h_exists_min : ∃ m : Fin r, ∑ i, (v m i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0 ∧ ∀ k : Fin r, k.val < m.val → ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r = 0 := by
        have h_nonempty : ∃ k : Fin r, ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0 := by
          use m
        obtain ⟨m, hm⟩ : ∃ m : Fin r, ∑ i, (v m i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0 ∧ ∀ k : Fin r, k.val < m.val → ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r = 0 := by
          have h_nonempty : ∃ k : Fin r, ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0 := h_nonempty
          have h_well_founded : WellFounded (fun k l : Fin r => k.val < l.val) := by
            exact wellFounded_lt
          have := h_well_founded.has_min { k : Fin r | ∑ i, ( v k i : ℝ ) * w i * u i ^ r ≠ 0 } ⟨ m, hm ⟩;
          exact ⟨ this.choose, this.choose_spec.1, fun k hk => Classical.not_not.1 fun hk' => this.choose_spec.2 k hk' hk ⟩;
        use m
      exact h_exists_min;
    use m;
  obtain ⟨e, he_pos, he_bound, he_vanish, he_comp⟩ : ∃ e : Fin m.val → ℕ, (∀ k, 1 ≤ e k) ∧ (∀ k, e k ≤ r - 1) ∧ (∀ k, ∀ j, j < r + e k → ∑ i, (v ⟨k.val, by omega⟩ i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧ (∀ k, ∑ i, ((v m i : ℤ) : ℝ) ^ 2 ≤ (M ^ (e k) / (Nat.factorial (e k) : ℝ)) ^ 2 * ∑ i, ((v ⟨k.val, by omega⟩ i : ℤ) : ℝ) ^ 2) := by
    choose! e he₁ he₂ he₃ he₄ using comparison_with_vanishing r hr s hs M u w hu_range hu_strict hw_pos v hv_kernel hv_indep hv_succ m hm.1 hm.2;
    exact ⟨ _, fun k => he₁ _ <| k.2, fun k => he₂ _ <| k.2, fun k => he₃ _ <| k.2, fun k => he₄ _ <| k.2 ⟩;
  have h_prod_bound : (∏ k : Fin m.val, (M ^ (e k) / (Nat.factorial (e k) : ℝ))) ≤ (∏ j ∈ Finset.range r, (M ^ j / (Nat.factorial j : ℝ))) := by
    apply_rules [ excess_product_bound ];
    · exact Nat.le_of_lt m.2;
    · linarith [ show ( s : ℝ ) ≥ 2 by norm_cast; linarith ];
    · exact le_trans ( by norm_num [ hs ] ; linarith ) hM;
    · apply_rules [ dim_constraint_from_vanishing ];
      · exact Nat.le_of_lt m.2;
      · exact hv_indep.comp _ ( fun a b h => by simpa [ Fin.ext_iff ] using h );
  refine' ⟨ m, hm.1, _ ⟩;
  refine le_trans ?_ ( mul_le_mul_of_nonneg_right ( pow_le_pow_left₀ ( Finset.prod_nonneg fun _ _ => div_nonneg ( pow_nonneg ( by linarith [ show ( s : ℝ ) ≥ 2 by norm_cast; linarith ] ) _ ) ( Nat.cast_nonneg _ ) ) h_prod_bound 2 ) ?_ );
  · convert multiply_comparison_bounds r ( fun k => ∑ i, ( v k i : ℝ ) ^ 2 ) ( fun k => Finset.sum_nonneg fun _ _ => sq_nonneg _ ) hv_mono m ( fun k => ( M ^ e k / ( e k |> Nat.factorial : ℝ ) ) ^ 2 ) ( fun k => sq_nonneg _ ) ( fun k => he_comp k ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
    rw [ Finset.prod_pow ];
  · exact Finset.prod_nonneg fun _ _ => Finset.sum_nonneg fun _ _ => sq_nonneg _