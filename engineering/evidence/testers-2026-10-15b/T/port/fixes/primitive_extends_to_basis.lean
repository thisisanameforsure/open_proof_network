lemma primitive_extends_to_basis
    (m s : ℕ) (hm : 2 ≤ m) (hms : m ≤ s)
    (z : Fin m → (Fin s → ℤ))
    (hz_indep : LinearIndependent ℤ z)
    (v : Fin s → ℤ)
    (hv_mem : v ∈ Submodule.span ℤ (Set.range z))
    (hv_prim : ∀ n : ℤ, ∀ w : Fin s → ℤ, w ∈ Submodule.span ℤ (Set.range z) →
      v = n • w → n = 1 ∨ n = -1) :
    ∃ w : Fin (m - 1) → (Fin s → ℤ),
      LinearIndependent ℤ (Fin.cons v w) ∧
      Submodule.span ℤ (Set.range (Fin.cons v w)) = Submodule.span ℤ (Set.range z) := by
  have h_basis : ∃ (u : Fin m → (Fin s → ℤ)), LinearIndependent ℤ u ∧ Submodule.span ℤ (Set.range u) = Submodule.span ℤ (Set.range z) ∧ u ⟨0, by linarith⟩ = v := by
    obtain ⟨c, hc⟩ : ∃ c : Fin m → ℤ, v = ∑ k, c k • z k := by
      rw [ Submodule.mem_span_range_iff_exists_fun ] at hv_mem ; tauto;
    obtain ⟨U, hU⟩ : ∃ U : Matrix (Fin m) (Fin m) ℤ, (∀ j, U ⟨0, by linarith⟩ j = c j) ∧ (U.det = 1 ∨ U.det = -1) := by
      apply int_vector_primitive_extends_unimodular m (by linarith) c;
      intro d hd; specialize hv_prim d ( ∑ k, ( c k / d ) • z k ) ; simp_all +decide [Finset.smul_sum] ;
      refine' hv_prim _ _;
      · exact Submodule.sum_mem _ fun i _ => Submodule.smul_mem _ _ ( Submodule.subset_span ( Set.mem_range_self _ ) );
      · exact Finset.sum_congr rfl fun i _ => by rw [ ← mul_assoc, ← Int.cast_mul, Int.mul_ediv_cancel' ( hd i ) ] ;
    refine' ⟨ fun i => ∑ j, U i j • z j, _, _, _ ⟩;
    · rw [ Fintype.linearIndependent_iff ] at *;
      intro g hg;
      have h_fubini : ∑ j, (∑ i, g i * U i j) • z j = 0 := by
        convert hg using 1;
        simp +decide only [mul_comm, Finset.sum_smul, Finset.smul_sum, smul_smul];
        exact Finset.sum_comm.trans ( Finset.sum_congr rfl fun _ _ => Finset.sum_congr rfl fun _ _ => by ring );
      have h_unimodular : ∀ (g : Fin m → ℤ), (∀ j, ∑ i, g i * U i j = 0) → ∀ i, g i = 0 := by
        intro g hg i
        have h_unimodular : Matrix.mulVec (Matrix.transpose U) g = 0 := by
          exact funext fun j => by simpa [ Matrix.mulVec, dotProduct, mul_comm ] using hg j;
        have h_unimodular : Matrix.det (Matrix.transpose U) ≠ 0 := by
          cases hU.2 <;> simp +decide [ * ];
        exact Matrix.eq_zero_of_mulVec_eq_zero h_unimodular ‹_› ▸ rfl;
      exact h_unimodular g fun j => hz_indep _ h_fubini j;
    · refine' le_antisymm _ _ <;> rw [ Submodule.span_le ] <;> simp +decide [ Set.range_subset_iff ];
      · exact fun i => Submodule.sum_mem _ fun j _ => Submodule.smul_mem _ _ ( Submodule.subset_span ( Set.mem_range_self _ ) );
      · intro i
        have h_inv : ∃ V : Matrix (Fin m) (Fin m) ℤ, V * U = 1 := by
          exact ⟨ U⁻¹, Matrix.nonsing_inv_mul _ <| isUnit_iff_dvd_one.mpr <| by rcases hU.2 with h | h <;> norm_num [ h ] ⟩;
        obtain ⟨ V, hV ⟩ := h_inv;
        have h_inv : z i = ∑ j, V i j • (∑ k, U j k • z k) := by
          have h_inv : ∀ i, ∑ j, V i j • (∑ k, U j k • z k) = ∑ k, (∑ j, V i j * U j k) • z k := by
            simp +decide [ Finset.smul_sum, Finset.sum_smul ];
            exact fun i => Finset.sum_comm.trans ( Finset.sum_congr rfl fun _ _ => Finset.sum_congr rfl fun _ _ => by ring );
          simp_all +decide [ ← Matrix.mul_apply, ← Matrix.ext_iff ];
          simp +decide [ Matrix.one_apply ];
        exact h_inv.symm ▸ Submodule.sum_mem _ fun j _ => Submodule.smul_mem _ _ ( Submodule.subset_span ⟨ j, rfl ⟩ );
    · grind;
  obtain ⟨u, hu_indep, hu_span, hu_v⟩ := h_basis;
  use fun i => u ⟨i.val + 1, by
    exact Nat.succ_lt_of_lt_pred i.2⟩;
  generalize_proofs at *;
  rcases m with ( _ | _ | m ) <;> simp_all +decide;
  refine' ⟨ _, _ ⟩;
  · convert hu_indep using 1;
    ext i; induction i using Fin.inductionOn <;> aesop;
  · convert hu_span using 2;
    ext x; simp;
    exact ⟨ fun hx => hx.elim ( fun hx => ⟨ 0, hx.symm ▸ hu_v ⟩ ) fun ⟨ y, hy ⟩ => ⟨ _, hy ⟩, fun hx => by rcases hx with ⟨ y, rfl ⟩ ; exact Fin.cases ( Or.inl <| by aesop ) ( fun y => Or.inr ⟨ y, rfl ⟩ ) y ⟩