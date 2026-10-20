lemma kernel_and_complement_exist
    (r : ℕ) (hr : 0 < r)
    (phi : (Fin (2 * r) → ℤ) →ₗ[ℤ] (Fin r → ℤ)) :
    ∃ (z w : Fin r → (Fin (2 * r) → ℤ)),
      (∀ k : Fin r, phi (z k) = 0) ∧
      LinearIndependent ℤ z ∧
      let Q : Matrix (Fin (2 * r)) (Fin (2 * r)) ℤ :=
        Matrix.of (fun i j =>
          if h : j.val < r then z ⟨j.val, h⟩ i
          else w ⟨j.val - r, by omega⟩ i)
      Q.det = 1 ∨ Q.det = -1 := by
  have h_basis : ∃ (b : Module.Basis (Fin (2 * r)) ℤ (Fin (2 * r) → ℤ)), (∀ k : Fin r, phi (b (Fin.castLE (by omega) k)) = 0) := by
    obtain ⟨K, W, hK, hW, h_compl⟩ : ∃ K W : Submodule ℤ (Fin (2 * r) → ℤ), K = LinearMap.ker phi ∧ IsCompl K W := by
      exact ⟨ _, _, rfl, kernel_has_complement _ _ _ |> Classical.choose_spec ⟩;
    obtain ⟨bK, hbK⟩ : ∃ bK : Module.Basis (Fin (Module.finrank ℤ K)) ℤ K, True := by
      exact ⟨ Module.finBasis ℤ K, trivial ⟩
    obtain ⟨bW, hbW⟩ : ∃ bW : Module.Basis (Fin (Module.finrank ℤ W)) ℤ W, True := by
      exact ⟨ Module.finBasis ℤ W, trivial ⟩;
    obtain ⟨b, hb⟩ : ∃ b : Module.Basis (Fin (Module.finrank ℤ K + Module.finrank ℤ W)) ℤ (Fin (2 * r) → ℤ), (∀ k : Fin (Module.finrank ℤ K), b (Fin.castLE (by omega) k) ∈ K) ∧ (∀ k : Fin (Module.finrank ℤ W), b (Fin.castLE (by omega) (Fin.addNat k (Module.finrank ℤ K))) ∈ W) := by
      have h_combined_basis : ∃ b : Module.Basis (Fin (Module.finrank ℤ K) ⊕ Fin (Module.finrank ℤ W)) ℤ (Fin (2 * r) → ℤ), (∀ k : Fin (Module.finrank ℤ K), b (Sum.inl k) ∈ K) ∧ (∀ k : Fin (Module.finrank ℤ W), b (Sum.inr k) ∈ W) := by
        refine' ⟨ _, _, _ ⟩;
        refine' ( bK.prod bW ).map _;
        refine' ( Submodule.prodEquivOfIsCompl K W _ );
        exact ⟨ hW, h_compl ⟩;
        · intro k; simp [Module.Basis.map_apply, Module.Basis.prod_apply, Submodule.coe_prodEquivOfIsCompl']
        · simp +decide [ Module.Basis.map ];
      obtain ⟨ b, hb₁, hb₂ ⟩ := h_combined_basis;
      refine' ⟨ b.reindex ( Equiv.ofBijective _ ⟨ _, _ ⟩ ), _, _ ⟩;
      use fun x => x.elim ( fun k => Fin.castLE ( by omega ) k ) ( fun k => Fin.castLE ( by omega ) ( k.addNat ( Module.finrank ℤ K ) ) );
      all_goals norm_num [ Function.Injective, Function.Surjective ];
      all_goals norm_num [ Fin.ext_iff, Fin.val_add ];
      exact ⟨ fun a b h => False.elim <| by linarith [ Fin.is_lt a, Fin.is_lt b ], fun b a h => False.elim <| by linarith [ Fin.is_lt a, Fin.is_lt b ] ⟩;
      exact fun x => if hx : x.val < Module.finrank ℤ K then Or.inl ⟨ ⟨ x.val, hx ⟩, rfl ⟩ else Or.inr ⟨ ⟨ x.val - Module.finrank ℤ K, by omega ⟩, by simp +decide [ Nat.sub_add_cancel ( show Module.finrank ℤ K ≤ x.val from le_of_not_gt hx ) ] ⟩;
      · intro k; convert hb₁ k using 1;
        congr! 1;
        (simp +decide [ Equiv.symm_apply_eq ]) <;> rfl
      · intro k; convert hb₂ k using 1;
        congr! 1;
        (simp +decide [ Equiv.symm_apply_eq ]) <;> rfl
    have h_rank : Module.finrank ℤ K + Module.finrank ℤ W = 2 * r := by
      convert Module.finrank_eq_card_basis b |> Eq.symm; all_goals norm_num;
    use b.reindex (finCongr h_rank);
    intro k; specialize hb; have := hb.1 ⟨ k, by linarith [ Fin.is_lt k, show Module.finrank ℤ K ≥ r from by
                                                                          have := ker_rank_ge_r r phi; aesop; ] ⟩ ; aesop;
  obtain ⟨ b, hb ⟩ := h_basis;
  refine' ⟨ fun k => b ( Fin.castLE ( by omega ) k ), fun k => b ( Fin.castLE ( by omega ) ( Fin.addNat k r ) ), _, _, _ ⟩ <;> simp_all +decide [ Fintype.linearIndependent_iff ];
  · intro g hg i; have := b.linearIndependent; simp_all +decide [ Fintype.linearIndependent_iff ] ;
    convert this ( fun x => if hx : x.val < r then g ⟨ x.val, hx ⟩ else 0 ) _ ⟨ i, by linarith [ Fin.is_lt i ] ⟩ using 1 ; simp +decide ;
    rw [ ← Finset.sum_subset ( Finset.subset_univ ( Finset.image ( fun x : Fin r => Fin.castLE ( by omega ) x ) Finset.univ ) ) ] <;> norm_num [ Finset.sum_image ];
    · rw [ Finset.sum_image ] ; aesop;
      exact fun x _ y _ h => by simpa [ Fin.ext_iff ] using h;
    · intro x hx; split_ifs <;> simp_all +decide [ Fin.ext_iff ] ;
      exact False.elim <| hx ⟨ x, by linarith ⟩ rfl;
  · have h_det : Matrix.det (Matrix.of (fun i j => b j i)) = 1 ∨ Matrix.det (Matrix.of (fun i j => b j i)) = -1 := by
      have h_det : IsUnit (Matrix.det (Matrix.of (fun i j => b j i))) := by
        have h_det : IsUnit (Matrix.det (Matrix.of (fun i j => b j i))) := by
          have h_basis : ∀ (v : Fin (2 * r) → ℤ), ∃ (c : Fin (2 * r) → ℤ), v = ∑ i, c i • b i := by
            exact fun v => ⟨ _, Eq.symm ( b.sum_repr v ) ⟩
          have h_det : ∀ (v : Fin (2 * r) → ℤ), ∃ (c : Fin (2 * r) → ℤ), v = Matrix.mulVec (Matrix.of (fun i j => b j i)) c := by
            intro v; obtain ⟨ c, hc ⟩ := h_basis v; use c; ext i; simp +decide [ hc, Matrix.mulVec, dotProduct ] ;
            grind +revert
          generalize_proofs at *;
          have h_det : Function.Surjective (Matrix.mulVec (Matrix.of (fun i j => b j i))) := by
            exact fun v => by obtain ⟨ c, rfl ⟩ := h_det v; exact ⟨ c, rfl ⟩ ;
          generalize_proofs at *;
          have h_det : ∃ (A : Matrix (Fin (2 * r)) (Fin (2 * r)) ℤ), Matrix.of (fun i j => b j i) * A = 1 := by
            exact Matrix.mulVec_surjective_iff_exists_right_inverse.mp h_det
          generalize_proofs at *;
          exact isUnit_iff_exists_inv.mpr ⟨ h_det.choose.det, by simpa using congr_arg Matrix.det h_det.choose_spec ⟩
        generalize_proofs at *;
        exact h_det;
      exact Int.isUnit_iff.mp h_det;
    convert h_det using 1;
    · congr! 2;
      ext i j; aesop;
    · congr! 2;
      ext i j; aesop