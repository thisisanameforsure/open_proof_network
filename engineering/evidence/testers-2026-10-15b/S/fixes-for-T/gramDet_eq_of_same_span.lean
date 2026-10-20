lemma gramDet_eq_of_same_span
    (m s : ℕ)
    (b1 b2 : Fin m → (Fin s → ℤ))
    (h1 : LinearIndependent ℤ b1)
    (h_span : Submodule.span ℤ (Set.range b1) = Submodule.span ℤ (Set.range b2)) :
    gramDet m s (fun k i => ((b1 k i : ℤ) : ℝ)) = gramDet m s (fun k i => ((b2 k i : ℤ) : ℝ)) := by
  obtain ⟨U, hU⟩ : ∃ U : Matrix (Fin m) (Fin m) ℤ, (∀ k, b1 k = ∑ j, U k j • b2 j) ∧ Int.natAbs U.det = 1 := by
    obtain ⟨U, hU⟩ : ∃ U : Matrix (Fin m) (Fin m) ℤ, (∀ k, b1 k = ∑ j, U k j • b2 j) := by
      have h_basis : ∀ k, b1 k ∈ Submodule.span ℤ (Set.range b2) := by
        exact fun k => h_span ▸ Submodule.subset_span ( Set.mem_range_self k );
      choose! U hU using fun k => Submodule.mem_span_range_iff_exists_fun ℤ |>.1 ( h_basis k );
      exact ⟨ U, fun k => hU k ▸ rfl ⟩;
    obtain ⟨V, hV⟩ : ∃ V : Matrix (Fin m) (Fin m) ℤ, (∀ k, b2 k = ∑ j, V k j • b1 j) := by
      have hV : ∀ k, b2 k ∈ Submodule.span ℤ (Set.range b1) := by
        exact fun k => h_span.symm ▸ Submodule.subset_span ( Set.mem_range_self k );
      choose V hV using fun k => ( Finsupp.mem_span_range_iff_exists_finsupp.mp ( hV k ) );
      exact ⟨ fun k j => V k j, fun k => by simpa [ Finsupp.sum_fintype ] using hV k |> Eq.symm ⟩;
    have hUV : U * V = 1 := by
      have hUV : ∀ k, b1 k = ∑ j, (U * V) k j • b1 j := by
        intro k
        rw [hU k]
        simp [Matrix.mul_apply, hV];
        simp +decide only [Finset.mul_sum _ _ _, Finset.sum_mul, mul_assoc];
        rw [ Finset.sum_comm ];
      have hUV : ∀ k j, (U * V) k j = if k = j then 1 else 0 := by
        intro k j;
        have := Fintype.linearIndependent_iff.mp h1 ( fun i => ( U * V ) k i - if k = i then 1 else 0 ) ?_;
        · exact eq_of_sub_eq_zero ( this j );
        · simp +decide [ sub_smul, Finset.sum_sub_distrib, hUV k ];
      exact Matrix.ext fun i j => by simpa [Matrix.one_apply] using hUV i j;
    have := congr_arg Matrix.det hUV; norm_num at this;
    exact ⟨ U, hU, by rw [ Int.mul_eq_one_iff_eq_one_or_neg_one ] at this; omega ⟩;
  convert gramDet_unimodular_change m s b2 U hU.2 using 3 ; aesop