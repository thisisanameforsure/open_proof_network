lemma successive_minima_inductive_step
    (m s : ℕ) (hm : 2 ≤ m) (hms : m ≤ s)
    (z : Fin m → (Fin s → ℤ))
    (hz_indep : LinearIndependent ℤ z)
    (ih : ∀ (m' : ℕ), m' < m → 1 ≤ m' → m' ≤ s →
      ∀ (z' : Fin m' → (Fin s → ℤ)), LinearIndependent ℤ z' →
        ∃ y : Fin m' → (Fin s → ℤ),
          (∀ k, y k ∈ Submodule.span ℤ (Set.range z')) ∧
          LinearIndependent ℝ (fun k : Fin m' => (fun i : Fin s => ((y k i : ℤ) : ℝ))) ∧
          Monotone (fun k : Fin m' => ∑ i : Fin s, ((y k i : ℤ) : ℝ) ^ 2) ∧
          ∏ k : Fin m', (∑ i : Fin s, ((y k i : ℤ) : ℝ) ^ 2) ≤
            (2 : ℝ) ^ (m' * (m' - 1)) *
            gramDet m' s (fun k i => ((z' k i : ℤ) : ℝ))) :
    ∃ y : Fin m → (Fin s → ℤ),
      (∀ k, y k ∈ Submodule.span ℤ (Set.range z)) ∧
      LinearIndependent ℝ (fun k : Fin m => (fun i : Fin s => ((y k i : ℤ) : ℝ))) ∧
      Monotone (fun k : Fin m => ∑ i : Fin s, ((y k i : ℤ) : ℝ) ^ 2) ∧
      ∏ k : Fin m, (∑ i : Fin s, ((y k i : ℤ) : ℝ) ^ 2) ≤
        (2 : ℝ) ^ (m * (m - 1)) *
        gramDet m s (fun k i => ((z k i : ℤ) : ℝ)) := by
  obtain ⟨v, hv_mem, hv_ne, hv_min⟩ := shortest_lattice_vector_exists m s (by omega) z hz_indep
  have hv_prim := shortest_is_primitive m s z v hv_mem hv_ne hv_min
  obtain ⟨w, hw_indep, hw_span⟩ := primitive_extends_to_basis m s hm hms z hz_indep v hv_mem hv_prim
  set w' : Fin (m - 1) → (Fin s → ℤ) := fun j i =>
    (∑ k, v k * v k) * w j i - (∑ k, w j k * v k) * v i with w'_def
  have hw'_indep : LinearIndependent ℤ w' := projected_int_vectors_indep (m - 1) s v hv_ne w hw_indep
  obtain ⟨ytil, hytil_mem, hytil_indep, _, hytil_bound⟩ :=
    ih (m - 1) (by omega) (by omega) (by omega) w' hw'_indep
  have hytil_coeffs : ∀ j, ∃ a : Fin (m - 1) → ℤ, ytil j = ∑ k, a k • w' k := by
    intro j
    have := hytil_mem j
    rw [Submodule.mem_span_range_iff_exists_fun] at this
    obtain ⟨c, hc⟩ := this; exact ⟨c, hc.symm⟩
  choose a ha using hytil_coeffs
  set l : Fin (m - 1) → (Fin s → ℤ) := fun j i => ∑ k, a j k * w k i with l_def
  have h_center : ∀ j, ∃ n : ℤ, |(∑ i, (l j i + n * v i) * v i : ℤ)| * 2 ≤ ∑ i, v i * v i := by
    intro j; exact integer_centering_exists s v (l j) hv_ne
  choose ctr hctr using h_center
  set zc : Fin (m - 1) → (Fin s → ℤ) := fun j i => l j i + ctr j * v i with zc_def
  set out : Fin m → (Fin s → ℤ) := fun k =>
    if h : k.val = 0 then v
    else zc ⟨k.val - 1, by omega⟩ with out_def
  have hytil_perp_v : ∀ j, ∑ i, (ytil j i : ℝ) * (v i : ℝ) = 0 := by
    intro j; rw [ ha j ] ; simp +decide [ Finset.sum_mul _ _ _, mul_comm ] ;
    rw [ Finset.sum_comm ] ; simp +decide [ w'_def, mul_sub, mul_assoc, mul_comm, mul_left_comm, Finset.mul_sum _ _ _ ] ;
    exact sub_eq_zero_of_eq ( Finset.sum_congr rfl fun _ _ => Finset.sum_comm.trans ( Finset.sum_congr rfl fun _ _ => Finset.sum_congr rfl fun _ _ => by ring ) )
  have hzc_ne : ∀ j, zc j ≠ 0 := by
    intro j hj_zero
    have hytil_zero : ytil j = 0 := by
      convert congr_arg ( fun x : Fin s → ℤ => fun i => ( ∑ k, ( v k * v k ) ) * x i - ( ∑ k, ( x k * v k ) ) * ( v i ) ) hj_zero using 1;
      · convert ha j using 1;
        ext i; simp +decide [ zc_def, l_def, w'_def ] ; ring_nf;
        simp +decide [ Finset.sum_add_distrib, Finset.mul_sum _ _ _, Finset.sum_mul _ _ _, mul_comm, mul_left_comm, sq ] ; ring_nf;
        simp +decide [ mul_comm, mul_left_comm, Finset.mul_sum _ _ _ ] ; ring_nf;
        exact congrArg₂ _ rfl ( Finset.sum_comm.trans ( Finset.sum_congr rfl fun _ _ => Finset.sum_congr rfl fun _ _ => by ring ) );
      · norm_num [ funext_iff ];
    exact hytil_indep.ne_zero j <| by ext i; simp +decide [ hytil_zero ] ;
  have hzc_not_mul_v : ∀ j, ¬ ∃ n : ℤ, ∀ i, zc j i = n * v i := by
    intro j hj
    obtain ⟨n, hn⟩ := hj
    have h_l_eq : l j = (n - ctr j) • v := by
      ext i; specialize hn i; norm_num at *; linarith;
    have h_ytil_zero : ytil j = 0 := by
      have h_ytil_zero : ytil j = (∑ k, v k * v k) • l j - (∑ k, l j k * v k) • v := by
        convert ha j using 1;
        ext i; simp +decide [ l_def, w'_def ] ; ring_nf;
        simp +decide [ mul_assoc, mul_comm, mul_left_comm, Finset.mul_sum _ _ _ ];
        exact Finset.sum_comm.trans ( Finset.sum_congr rfl fun _ _ => Finset.sum_congr rfl fun _ _ => by ring );
      simp +decide [ h_ytil_zero, h_l_eq ];
      simp +decide [ mul_assoc, mul_comm, mul_left_comm, Finset.mul_sum _ _ _ ];
    exact hytil_indep.ne_zero j ( by ext i; simp +decide [ h_ytil_zero ] )
  have h_mem : ∀ k, out k ∈ Submodule.span ℤ (Set.range z) := by
    intro k; by_cases hk : k.val = 0 <;> simp +decide [ hk, out_def, hv_mem ] ;
    refine' hw_span ▸ Submodule.add_mem _ _ _;
    · rw [ Submodule.mem_span ];
      intro p hp;
      convert p.sum_mem fun i _ => p.smul_mem ( a ⟨ k - 1, by omega ⟩ i ) ( hp <| Set.mem_range_self <| Fin.succ i ) using 1;
      any_goals exact Finset.univ;
      exact funext fun i => by simp +decide [ l_def, Fin.cons ] ;
    · exact Submodule.smul_mem _ _ ( Submodule.subset_span ( Set.mem_range_self 0 ) )
  have h_indep : LinearIndependent ℝ (fun k : Fin m => (fun i : Fin s => ((out k i : ℤ) : ℝ))) := by
    have h_linearInd : ∀ (c : Fin m → ℝ), (∑ k : Fin m, c k • (fun i : Fin s => ((out k i : ℤ) : ℝ))) = 0 → c = 0 := by
      intro c hc
      have h_sum : ∑ j : Fin (m - 1), c ⟨j + 1, by omega⟩ • (fun i : Fin s => ((ytil j i : ℤ) : ℝ)) = 0 := by
        have h_sum : ∑ j : Fin (m - 1), c ⟨j + 1, by omega⟩ • (fun i : Fin s => ((ytil j i : ℤ) : ℝ)) = (fun i : Fin s => ((∑ k, v k * v k) : ℝ) * (∑ j : Fin (m - 1), c ⟨j + 1, by omega⟩ * (zc j i : ℝ)) - (∑ j : Fin (m - 1), c ⟨j + 1, by omega⟩ * (∑ i : Fin s, (zc j i : ℝ) * (v i : ℝ))) * (v i : ℝ)) := by
          have hy : ∀ j i, ytil j i = (∑ k, v k * v k) * zc j i - (∑ i', zc j i' * v i') * v i := by
            intro j i
            have h1 : ytil j i = ∑ k, a j k * ((∑ k', v k' * v k') * w k i - (∑ k', w k k' * v k') * v i) := by
              rw [ha j]; simp [w'_def, Finset.sum_apply]
            have h2 : ∑ i', zc j i' * v i' = ∑ k, a j k * (∑ k', w k k' * v k') + ctr j * ∑ k', v k' * v k' := by
              simp only [zc_def, l_def, add_mul, Finset.sum_add_distrib, Finset.sum_mul, Finset.mul_sum]
              rw [Finset.sum_comm]
              congr 1
              · exact Finset.sum_congr rfl fun _ _ => Finset.sum_congr rfl fun _ _ => by ring
              · exact Finset.sum_congr rfl fun _ _ => by ring
            have h3 : zc j i = ∑ k, a j k * w k i + ctr j * v i := rfl
            have e1 : ∀ k, a j k * ((∑ k', v k' * v k') * w k i - (∑ k', w k k' * v k') * v i)
                = (∑ k', v k' * v k') * (a j k * w k i) - (a j k * ∑ k', w k k' * v k') * v i :=
              fun k => by ring
            rw [h1, h2, h3, Finset.sum_congr rfl (fun k _ => e1 k), Finset.sum_sub_distrib,
              ← Finset.mul_sum, ← Finset.sum_mul]
            ring
          ext i
          simp only [Finset.sum_apply, Pi.smul_apply, smul_eq_mul, hy]
          push_cast
          simp only [Finset.mul_sum, Finset.sum_mul, mul_sub, Finset.sum_sub_distrib]
          congr 1
          · exact Finset.sum_congr rfl fun _ _ => Finset.sum_congr rfl fun _ _ => by ring
          · exact Finset.sum_congr rfl fun _ _ => Finset.sum_congr rfl fun _ _ => by ring
        have h_sum_zero : ∑ j : Fin (m - 1), c ⟨j + 1, by omega⟩ • (fun i : Fin s => ((zc j i : ℤ) : ℝ)) = -c ⟨0, by omega⟩ • (fun i : Fin s => ((v i : ℤ) : ℝ)) := by
          rcases m with ( _ | _ | m ) <;> norm_num [ Fin.sum_univ_succ ] at *;
          · contradiction;
          · contradiction;
          · convert eq_neg_of_add_eq_zero_right hc using 1;
            erw [ Fin.sum_univ_succ ] ; norm_num [ Fin.sum_univ_succ ] ; ring!;
            all_goals simp [out_def]
        have h_sum_zero : ∑ j : Fin (m - 1), c ⟨j + 1, by omega⟩ * (∑ i : Fin s, (zc j i : ℝ) * (v i : ℝ)) = -c ⟨0, by omega⟩ * (∑ i : Fin s, (v i : ℝ) * (v i : ℝ)) := by
          convert congr_arg ( fun f : Fin s → ℝ => ∑ i, f i * ( v i : ℝ ) ) h_sum_zero using 1 <;> norm_num [ Finset.sum_mul _ _ _ ];
          · rw [ Finset.sum_comm ] ; exact Finset.sum_congr rfl fun _ _ => by rw [ Finset.mul_sum _ _ _ ] ; exact Finset.sum_congr rfl fun _ _ => by ring;
          · simp +decide only [Finset.mul_sum _ _ _, mul_assoc];
        convert h_sum using 1;
        ext i; simp +decide [ h_sum_zero ] ; ring_nf;
        rename_i h; replace h := congr_fun h i; simp +decide [ mul_comm] at h;
        simp +decide [ add_comm, h ] ; ring;
      have h_c_zero : ∀ j : Fin (m - 1), c ⟨j + 1, by omega⟩ = 0 := by
        exact fun j => Fintype.linearIndependent_iff.mp hytil_indep _ h_sum j;
      ext ⟨ i, hi ⟩ ; induction i <;> simp +decide [ * ] at *;
      · rw [ Finset.sum_eq_single ⟨ 0, hi ⟩ ] at hc <;> simp +decide at hc ⊢;
        · exact hc.resolve_right fun h => hv_ne <| funext fun i => by simpa using congr_fun h i;
        · intro b hb; rcases b with ⟨ _ | b, hb ⟩ <;> simp +decide [ Fin.ext_iff ] at hb ⊢;
          exact Or.inl <| h_c_zero ⟨ b, Nat.lt_pred_iff.mpr ‹_› ⟩;
      · exact h_c_zero ⟨ _, Nat.lt_pred_iff.mpr hi ⟩;
    rw [ Fintype.linearIndependent_iff ] ; tauto
  have product_bound_qed : ∏ k : Fin m, (∑ i : Fin s, ((out k i : ℤ) : ℝ) ^ 2) ≤
      (2 : ℝ) ^ (m * (m - 1)) * gramDet m s (fun k i => ((z k i : ℤ) : ℝ)) := by
    have hzc_bound : ∀ j, (∑ i, (zc j i : ℝ) ^ 2) ≤ 4 * (∑ i, (ytil j i : ℝ) ^ 2) / (∑ i, (v i : ℝ) ^ 2) ^ 2 := by
      intro j
      have h_centering : (∑ i, ((zc j i : ℤ) : ℝ) ^ 2) - (∑ i, ((zc j i : ℤ) : ℝ) * ((v i : ℤ) : ℝ)) ^ 2 / (∑ i, ((v i : ℤ) : ℝ) ^ 2) = (∑ i, ((ytil j i : ℤ) : ℝ) ^ 2) / (∑ i, ((v i : ℤ) : ℝ) ^ 2) ^ 2 := by
        convert projection_norm_via_scaled s v ( l j ) hv_ne using 1;
        · convert projection_add_multiple_invariant s v ( l j ) ( ctr j ) using 1;
        · simp +decide [ ha, l_def, w'_def ];
          simp +decide [ mul_sub, mul_assoc, mul_comm, Finset.mul_sum _ _ _ ];
          simp +decide only [sq, mul_comm, mul_left_comm];
          simp +decide only [← mul_assoc];
          congr! 3; all_goals exact congrArg₂ _ rfl ( Finset.sum_comm.trans ( Finset.sum_congr rfl fun _ _ => Finset.sum_congr rfl fun _ _ => by ring ) );
      have h_centering_bound : (∑ i, ((zc j i : ℤ) : ℝ) ^ 2) - (∑ i, ((zc j i : ℤ) : ℝ) * ((v i : ℤ) : ℝ)) ^ 2 / (∑ i, ((v i : ℤ) : ℝ) ^ 2) ≥ (∑ i, ((zc j i : ℤ) : ℝ) ^ 2) / 4 := by
        have h_centering_bound : (∑ i, ((zc j i : ℤ) : ℝ) * ((v i : ℤ) : ℝ)) ^ 2 ≤ (∑ i, ((v i : ℤ) : ℝ) ^ 2) ^ 2 / 4 := by
          have h_centering_bound : |∑ i, ((zc j i : ℤ) : ℝ) * ((v i : ℤ) : ℝ)| ≤ (∑ i, ((v i : ℤ) : ℝ) ^ 2) / 2 := by
            norm_cast;
            rw [ Rat.divInt_eq_div, le_div_iff₀ ] <;> norm_cast;
            simpa only [ sq ] using hctr j;
          nlinarith only [ abs_le.mp h_centering_bound ];
        have h_centering_bound : (∑ i, ((zc j i : ℤ) : ℝ) ^ 2) ≥ (∑ i, ((v i : ℤ) : ℝ) ^ 2) := by
          apply hv_min;
          · convert h_mem ⟨ j + 1, by omega ⟩ using 1; simp [out_def]
          · exact hzc_ne j;
        rw [ sub_div', ge_iff_le, div_le_div_iff₀ ] <;> nlinarith [ show 0 < ∑ i : Fin s, ( v i : ℝ ) ^ 2 from lt_of_le_of_ne ( Finset.sum_nonneg fun _ _ => sq_nonneg _ ) ( Ne.symm <| by intro h; exact hv_ne <| by ext i; simpa [ sq ] using Finset.sum_eq_zero_iff_of_nonneg ( fun _ _ => sq_nonneg _ ) |>.1 h i ) ];
      ring_nf at *; linarith;
    have h_combined : (∏ k : Fin m, (∑ i : Fin s, ((out k i : ℤ) : ℝ) ^ 2)) ≤
      (∑ i : Fin s, ((v i : ℤ) : ℝ) ^ 2) * (4 / (∑ i : Fin s, ((v i : ℤ) : ℝ) ^ 2) ^ 2) ^ (m - 1) *
      (∏ k : Fin (m - 1), (∑ i : Fin s, ((ytil k i : ℤ) : ℝ) ^ 2)) := by
        have h_split : (∏ k : Fin m, (∑ i : Fin s, ((out k i : ℤ) : ℝ) ^ 2)) = (∑ i : Fin s, ((v i : ℤ) : ℝ) ^ 2) * (∏ j : Fin (m - 1), (∑ i : Fin s, ((zc j i : ℤ) : ℝ) ^ 2)) := by
          rcases m with ⟨ ⟩ <;> norm_num [ Fin.prod_univ_succ ] at *;
          · contradiction;
          · simp +decide [ out_def ];
        rw [ h_split, mul_assoc ];
        gcongr;
        convert Finset.prod_le_prod ?_ fun j _ => hzc_bound j using 1;
        · norm_num [ div_eq_mul_inv, mul_pow, mul_assoc, mul_comm, mul_left_comm, Finset.prod_mul_distrib ];
        · exact fun _ _ => Finset.sum_nonneg fun _ _ => sq_nonneg _;
    have hw'_gramDet : gramDet (m - 1) s (fun k i => ((w' k i : ℤ) : ℝ)) =
      (∑ i : Fin s, ((v i : ℤ) : ℝ) ^ 2) ^ (2 * (m - 1) - 1) *
      gramDet m s (fun k i => ((z k i : ℤ) : ℝ)) := by
        convert gramDet_projected_identity ( m - 1 ) s ( by omega ) v hv_ne w hw_indep using 1;
        · norm_num [ w'_def, sq ];
        · rcases m with ( _ | _ | m ) <;> norm_num at *;
          · contradiction;
          · contradiction;
          · left;
            convert gramDet_eq_of_same_span ( m + 1 + 1 ) s z ( Fin.cons v w ) hz_indep _ using 1;
            · congr! 2;
              rename_i k; induction k using Fin.inductionOn <;> simp +decide [ * ] ;
            · convert hw_span.symm using 1;
              congr with x ; simp +decide [ Fin.exists_fin_succ ];
    refine le_trans h_combined ?_;
    convert mul_le_mul_of_nonneg_left hytil_bound _ using 1;
    · rcases m with ( _ | _ | m ) <;> simp +decide [ Nat.mul_succ, pow_succ' ] at *;
      · contradiction;
      · contradiction;
      · rw [ hw'_gramDet ] ; ring_nf;
        field_simp;
        by_cases h : ∑ x : Fin s, ( v x : ℝ ) ^ 2 = 0 <;> simp +decide [h, mul_comm,
          mul_left_comm, pow_mul', div_eq_mul_inv];
        · exact False.elim <| hv_ne <| funext fun i => by norm_cast at h; simpa [ sq ] using Finset.sum_eq_zero_iff_of_nonneg ( fun _ _ => sq_nonneg _ ) |>.1 h i;
        · norm_num [ ← mul_assoc, ← mul_pow ];
    · exact mul_nonneg ( Finset.sum_nonneg fun _ _ => sq_nonneg _ ) ( pow_nonneg ( div_nonneg zero_le_four ( sq_nonneg _ ) ) _ )
  exact add_monotone m s z out h_mem h_indep product_bound_qed