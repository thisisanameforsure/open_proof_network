lemma integer_kernel_has_r_independent_vectors
    (r : ℕ) (hr : 2 ≤ r)
    (s : ℕ) (hs : s = 2 * r)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_strict : StrictMono u)
    (hw_pos : ∀ i, 0 < w i) :
    ∃ v : Fin r → (Fin s → ℤ),
      (∀ (k : Fin r) (j : ℕ), j < r →
        ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧
      LinearIndependent ℝ (fun k : Fin r => (fun i : Fin s => ((v k i : ℤ) : ℝ))) := by
  set B₀ : Matrix (Fin r) (Fin r) ℤ := fun j k => w ⟨r + k.val, by omega⟩ * (u ⟨r + k.val, by omega⟩ : ℤ) ^ j.val;
  obtain ⟨v, hv⟩ : ∃ v : Fin r → Fin s → ℤ, (∀ j₀ : Fin r, ∀ j : ℕ, j < r → ∑ i, (v j₀ i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧ (∀ j₀ j₁ : Fin r, j₀ ≠ j₁ → v j₀ ⟨j₁.val, by omega⟩ = 0) ∧ (∀ j₀ : Fin r, v j₀ ⟨j₀.val, by omega⟩ = B₀.det) := by
    refine' ⟨ fun j₀ i => if h : i.val < r then if h' : i.val = j₀.val then B₀.det else 0 else -Matrix.det ( Matrix.updateCol B₀ ( ⟨ i.val - r, by omega ⟩ : Fin r ) ( fun j => w ⟨ j₀.val, by omega ⟩ * ( u ⟨ j₀.val, by omega ⟩ : ℤ ) ^ j.val ) ), _, _, _ ⟩ <;> simp +decide ;
    · intro j₀ j hj;
      have h_split_sum : ∑ x : Fin s, (if h : x.val < r then if h' : x.val = j₀.val then B₀.det else 0 else -Matrix.det (Matrix.updateCol B₀ (⟨x.val - r, by omega⟩ : Fin r) (fun j => w ⟨j₀.val, by omega⟩ * (u ⟨j₀.val, by omega⟩ : ℤ) ^ j.val))) * (w x : ℝ) * ((u x : ℝ)) ^ j = ∑ x : Fin r, (B₀.det : ℝ) * (w ⟨x.val, by omega⟩ : ℝ) * ((u ⟨x.val, by omega⟩ : ℝ)) ^ j * (if x.val = j₀.val then 1 else 0) + ∑ x : Fin r, (-Matrix.det (Matrix.updateCol B₀ x (fun j => w ⟨j₀.val, by omega⟩ * (u ⟨j₀.val, by omega⟩ : ℤ) ^ j.val))) * (w ⟨r + x.val, by omega⟩ : ℝ) * ((u ⟨r + x.val, by omega⟩ : ℝ)) ^ j := by
        rw [ show ( Finset.univ : Finset ( Fin s ) ) = Finset.image ( fun x : Fin r => ⟨ x.val, by omega ⟩ ) Finset.univ ∪ Finset.image ( fun x : Fin r => ⟨ r + x.val, by omega ⟩ ) Finset.univ from ?_, Finset.sum_union ];
        · rw [ Finset.sum_image, Finset.sum_image ] <;> simp +decide ;
          · exact fun x y h => by simpa [ Fin.ext_iff ] using h;
          · exact fun x y h => Fin.ext <| by simpa using congr_arg Fin.val h;
        · norm_num [ Finset.disjoint_left ];
          exact fun a x => by linarith [ Fin.is_lt a, Fin.is_lt x ] ;
        · ext ⟨ x, hx ⟩ ; simp +decide [ Fin.ext_iff ];
          exact if h : x < r then Or.inl ⟨ ⟨ x, by linarith ⟩, rfl ⟩ else Or.inr ⟨ ⟨ x - r, by omega ⟩, by rw [ add_tsub_cancel_of_le ( by linarith ) ] ⟩;
      have h_det_sum : ∑ x : Fin r, Matrix.det (Matrix.updateCol B₀ x (fun j => w ⟨j₀.val, by omega⟩ * (u ⟨j₀.val, by omega⟩ : ℤ) ^ j.val)) * (w ⟨r + x.val, by omega⟩ : ℝ) * ((u ⟨r + x.val, by omega⟩ : ℝ)) ^ j = Matrix.det B₀ * (w ⟨j₀.val, by omega⟩ : ℝ) * ((u ⟨j₀.val, by omega⟩ : ℝ)) ^ j := by
        have h_det_sum : Matrix.mulVec B₀ (fun x : Fin r => Matrix.det (Matrix.updateCol B₀ x (fun j => w ⟨j₀.val, by omega⟩ * (u ⟨j₀.val, by omega⟩ : ℤ) ^ j.val))) = Matrix.det B₀ • (fun j => w ⟨j₀.val, by omega⟩ * (u ⟨j₀.val, by omega⟩ : ℤ) ^ j.val) := by
          rw [← Matrix.mulVec_cramer]
          first | rfl | (congr 1; funext x; rw [Matrix.cramer_apply]) | (congr 1; funext x) | congr 1
        convert congr_arg ( fun x : Fin r → ℤ => ( x ⟨ j, by linarith ⟩ : ℝ ) ) h_det_sum using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) <;> norm_num [ Matrix.mulVec, dotProduct ] ; ring_nf;
        · exact Finset.sum_congr rfl fun _ _ => by push_cast [ B₀ ] ; ring;
        · ring;
      simp_all +decide [ Fin.val_inj ];
    · exact fun j₀ j₁ hij h => False.elim <| hij <| Fin.ext h.symm;
  have h_det_B₀ : B₀.det ≠ 0 := by
    have h_det_B₀ : Matrix.det B₀ = Matrix.det (Matrix.of (fun j k : Fin r => (u ⟨r + k.val, by omega⟩ : ℤ) ^ j.val)) * ∏ k : Fin r, (w ⟨r + k.val, by omega⟩ : ℤ) := by
      erw [ Matrix.det_mul_row ];
      ring!;
    rw [ h_det_B₀ ];
    erw [ Matrix.det_transpose, Matrix.det_vandermonde ];
    exact mul_ne_zero ( Finset.prod_ne_zero_iff.mpr fun i hi => Finset.prod_ne_zero_iff.mpr fun j hj => sub_ne_zero_of_ne <| hu_strict.injective.ne <| by simpa [ Fin.ext_iff ] using ne_of_gt <| Finset.mem_Ioi.mp hj ) <| Finset.prod_ne_zero_iff.mpr fun i hi => Nat.cast_ne_zero.mpr <| ne_of_gt <| hw_pos _;
  refine' ⟨ v, hv.1, Fintype.linearIndependent_iff.2 _ ⟩;
  intro g hg i; replace hg := congr_fun hg ⟨ i, by linarith [ Fin.is_lt i ] ⟩ ; simp_all +decide [ Finset.sum_eq_single i ] ;