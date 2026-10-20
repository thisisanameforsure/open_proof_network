lemma successive_minima_in_kernel
    (r : ℕ) (hr : 2 ≤ r)
    (s : ℕ) (hs : s = 2 * r)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_strict : StrictMono u) (hw_pos : ∀ i, 0 < w i) :
    ∃ v : Fin r → (Fin s → ℤ),
      (∀ (k : Fin r) (j : ℕ), j < r →
        ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧
      (LinearIndependent ℝ (fun k : Fin r => (fun i : Fin s => ((v k i : ℤ) : ℝ)))) ∧
      (Monotone (fun k : Fin r => ∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2)) ∧
      (∀ k : Fin r, ∀ x : Fin s → ℤ,
        (∀ j : ℕ, j < r → ∑ i, (x i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) →
        (fun i : Fin s => (x i : ℝ)) ∉
          Submodule.span ℝ ((fun j : Fin r => fun i : Fin s => (v j i : ℝ)) ''
            { j | j.val < k.val }) →
        ∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2 ≤ ∑ i : Fin s, ((x i : ℤ) : ℝ) ^ 2) := by
  have := @integer_kernel_has_r_independent_vectors r hr s hs u w hu_strict hw_pos;
  have h_ind : ∀ k : Fin (r + 1), ∃ v : Fin k → (Fin s → ℤ), (∀ j : Fin k, ∀ l < r, ∑ i, (v j i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ l = 0) ∧ LinearIndependent ℝ (fun j : Fin k => (fun i : Fin s => ((v j i : ℤ) : ℝ))) ∧ Monotone (fun j : Fin k => ∑ i, ((v j i : ℤ) : ℝ) ^ 2) ∧ ∀ j : Fin k, ∀ x : Fin s → ℤ, (∀ l < r, ∑ i, (x i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ l = 0) → (fun i : Fin s => (x i : ℝ)) ∉ Submodule.span ℝ (Set.image (fun l : Fin k => (fun i : Fin s => ((v l i : ℤ) : ℝ))) {l | l.val < j.val}) → ∑ i, ((v j i : ℤ) : ℝ) ^ 2 ≤ ∑ i, ((x i : ℤ) : ℝ) ^ 2 := by
    intro k;
    induction' k using Fin.induction with k ih;
    · simp +decide [ Monotone ];
    · obtain ⟨ v, hv₁, hv₂, hv₃, hv₄ ⟩ := ih;
      obtain ⟨ x, hx₁, hx₂, hx₃ ⟩ := min_norm_kernel_vector_exists r s hr hs u w hu_strict hw_pos ( Submodule.span ℝ ( Set.range ( fun j : Fin k.castSucc => fun i : Fin s => ( v j i : ℝ ) ) ) ) ( by
        rw [ finrank_span_eq_card ] <;> norm_num [ hv₂ ] );
      refine' ⟨ Fin.snoc v x, _, _, _, _ ⟩;
      · intro j l hl; refine' Fin.lastCases _ _ j <;> simp +decide [ * ] ;
      · rw [ Fintype.linearIndependent_iff ] at *;
        intro g hg;
        simp +decide [ Fin.sum_univ_castSucc, funext_iff ] at hg ⊢;
        have hg_last : g (Fin.last k) = 0 := by
          contrapose! hx₂;
          rw [ Submodule.mem_span ];
          intro p hp;
          convert p.smul_mem ( - ( g ( Fin.last k ) ) ⁻¹ ) ( p.add_mem ( p.sum_mem fun i _ => p.smul_mem ( g ( Fin.castSucc i ) ) ( hp <| Set.mem_range_self i ) ) ( p.zero_mem ) ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; ext i ; simp +decide ;
          rw [ inv_mul_eq_div, neg_div', eq_div_iff hx₂ ] ; linarith [ hg i ];
        intro i; induction i using Fin.lastCases <;> simp +decide [ * ] at *;
        exact hv₂ _ ( by ext; simpa [ Finset.sum_apply, mul_comm ] using hg _ ) _;
      · intro i j hij;
        by_cases hi : i.val < k.val <;> by_cases hj : j.val < k.val <;> simp +decide [ *, Fin.snoc ] at hij ⊢;
        · exact hv₃ (by first | (simp only [Fin.le_def, Fin.coe_castLT] at hij ⊢; omega) | simpa [Fin.le_def] using hij | exact hij)
        · convert hv₄ ( Fin.castLT i hi ) x hx₁ _ using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
          refine' fun h => hx₂ _;
          exact Submodule.span_mono ( Set.image_subset_range _ _ ) h;
        · grind;
      · intro j y hy₁ hy₂;
        by_cases hj : j.val < k.val;
        · convert hv₄ ⟨ j, hj ⟩ y hy₁ _ using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
          · simp +decide [ Fin.snoc, hj ];
            congr!;
          · contrapose! hy₂;
            refine' Submodule.span_le.mpr _ hy₂;
            rintro _ ⟨ l, hl, rfl ⟩;
            exact Submodule.subset_span ⟨ ⟨ l, by
              exact lt_of_lt_of_le l.2 ( Nat.le_succ _ ) ⟩, by
              exact hl, by
              simp +decide [ Fin.snoc ] ⟩;
        · convert hx₃ y hy₁ _ using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
          · simp +decide [ Fin.eq_last_of_not_lt hj, int_sq_norm ];
            norm_cast;
            norm_num [ ← Int.ofNat_le, Int.natAbs_pow ];
          · contrapose! hy₂;
            refine' Submodule.span_le.mpr _ hy₂;
            rintro _ ⟨ j, rfl ⟩;
            refine' Submodule.subset_span ⟨ Fin.castSucc j, _, _ ⟩ <;> simp +decide [ Fin.snoc ];
            exact lt_of_lt_of_le ( Fin.castSucc_lt_last j ) ( Nat.le_of_not_lt hj );
  exact h_ind ⟨ r, Nat.lt_succ_self r ⟩