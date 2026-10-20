lemma annihilator_short_vectors
    (r : ℕ) (hr : 2 ≤ r)
    (s : ℕ) (hs : s = 2 * r)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_nonneg : ∀ i, 0 ≤ u i)
    (hu_strict : StrictMono u)
    (hw_pos : ∀ i, 0 < w i) :
    ∃ y : Fin r → (Fin s → ℤ),
      (∀ (k : Fin r) (j : ℕ), j < r →
        ∑ i, (y k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧
      (LinearIndependent ℝ (fun k : Fin r => (fun i : Fin s => ((y k i : ℤ) : ℝ)))) ∧
      (Monotone (fun k : Fin r => ∑ i : Fin s, ((y k i : ℤ) : ℝ) ^ 2)) ∧
      ∏ k : Fin r, (∑ i : Fin s, ((y k i : ℤ) : ℝ) ^ 2) ≤
        (2 : ℝ) ^ (r * (r - 1)) *
        ∏ j ∈ Finset.range r,
          (∑ i : Fin s, ((w i : ℝ) * (Nat.choose (u i).toNat j : ℝ)) ^ 2) := by
  obtain ⟨y, hy⟩ := orthogonal_lattice_short_vectors r (by linarith) s (by
  omega) (fun j => fun i => ((w i : ℤ) * (Nat.choose (u i).toNat j : ℤ))) (by
  refine' Fintype.linearIndependent_iff.2 _;
  intro g hg i
  have h_poly : ∀ i_1 : Fin s, ∑ j : Fin r, g j * (Nat.choose (u i_1).toNat j : ℝ) = 0 := by
    intro i_1; replace hg := congr_fun hg i_1; simp_all +decide [ mul_comm] ;
    convert congr_arg ( fun x : ℝ => x / ( w i_1 : ℝ ) ) hg using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) <;> norm_num [ Finset.sum_div _ _ _, mul_div_assoc, ne_of_gt ( hw_pos i_1 ) ];
  have h_poly_roots : ∀ x : ℕ, x ∈ Finset.image (fun i => (u i).toNat) Finset.univ → ∑ j : Fin r, g j * (Nat.choose x j : ℝ) = 0 := by
    aesop;
  have h_poly_zero : ∀ x : ℕ, ∑ j : Fin r, g j * (Nat.choose x j : ℝ) = 0 := by
    intro x
    by_contra h_nonzero_poly
    have h_poly_roots_card : Finset.card (Finset.image (fun i => (u i).toNat) Finset.univ) ≥ r := by
      rw [ Finset.card_image_of_injective _ fun i j hij => _ ] <;> norm_num [ Fin.ext_iff, hu_strict.injective.eq_iff ] at * ; linarith;
      exact fun i j hij => by simpa [ Fin.ext_iff ] using hu_strict.injective ( by linarith [ Int.toNat_of_nonneg ( hu_nonneg i ), Int.toNat_of_nonneg ( hu_nonneg j ) ] : u i = u j ) ;
    have h_poly_roots_card : Finset.card (Finset.filter (fun x => ∑ j : Fin r, g j * (Nat.choose x j : ℝ) = 0) (Finset.range (Finset.sup (Finset.image (fun i => (u i).toNat) Finset.univ) id + 1))) ≥ r := by
      refine' le_trans h_poly_roots_card ( Finset.card_le_card _ );
      exact fun x hx => Finset.mem_filter.mpr ⟨ Finset.mem_range.mpr ( Nat.lt_succ_of_le ( Finset.le_sup ( f := id ) hx ) ), h_poly_roots x hx ⟩
    have h_poly_roots_card : Finset.card (Finset.filter (fun x => ∑ j : Fin r, g j * (Nat.choose x j : ℝ) = 0) (Finset.range (Finset.sup (Finset.image (fun i => (u i).toNat) Finset.univ) id + 1))) < r := by
      have h_poly_roots_card : ∃ p : Polynomial ℝ, p.degree < r ∧ ∀ x : ℕ, ∑ j : Fin r, g j * (Nat.choose x j : ℝ) = p.eval (x : ℝ) := by
        use ∑ j : Fin r, Polynomial.C (g j) * (Polynomial.C (1 / (Nat.factorial j : ℝ)) * ∏ k ∈ Finset.range j, (Polynomial.X - Polynomial.C (k : ℝ)));
        refine' ⟨ lt_of_le_of_lt ( Polynomial.degree_sum_le _ _ ) _, _ ⟩;
        · erw [ Finset.sup_lt_iff ] ; norm_num [ Polynomial.degree_prod ];
          · intro j; by_cases hj : g j = 0 <;> simp +decide [ hj, Polynomial.degree_C ] ;
            exact lt_of_le_of_lt ( add_le_add ( Polynomial.degree_C_le ) ( Finset.sum_le_sum fun _ _ => Polynomial.degree_X_sub_C_le _ ) ) ( by norm_cast; simp );
          · exact WithBot.bot_lt_coe r;
        · intro x; simp +decide [ Polynomial.eval_finset_sum, Polynomial.eval_mul, Polynomial.eval_prod, Polynomial.eval_sub, Polynomial.eval_X, Polynomial.eval_C ] ;
          refine' Finset.sum_congr rfl fun j hj => _;
          by_cases hx : x < j.val <;> simp_all +decide [ Nat.choose_eq_zero_of_lt ];
          · exact Or.inr <| Or.inr <| Finset.prod_eq_zero ( Finset.mem_range.mpr hx ) <| sub_self _;
          · field_simp;
            rw_mod_cast [ mul_comm, ← Nat.descFactorial_eq_factorial_mul_choose ];
            rw [ Nat.descFactorial_eq_prod_range ] ; norm_num [ Int.subNatNat_eq_coe ];
            exact Or.inl ( Finset.prod_congr rfl fun i hi => by rw [ Nat.cast_sub ( by linarith [ Finset.mem_range.mp hi ] ) ] );
      obtain ⟨ p, hp_deg, hp_eval ⟩ := h_poly_roots_card; simp_all +decide [ Polynomial.eval_eq_sum_range ] ;
      have h_poly_roots_card : Finset.card (Finset.filter (fun x : ℕ => p.eval (x : ℝ) = 0) (Finset.range (Finset.sup (Finset.image (fun i => (u i).toNat) Finset.univ) id + 1))) ≤ p.natDegree := by
        have h_poly_roots_card : Finset.card (Finset.image (fun x : ℕ => (x : ℝ)) (Finset.filter (fun x : ℕ => p.eval (x : ℝ) = 0) (Finset.range (Finset.sup (Finset.image (fun i => (u i).toNat) Finset.univ) id + 1)))) ≤ p.natDegree := by
          exact le_trans ( Finset.card_le_card <| show _ ⊆ p.roots.toFinset from by aesop_cat ) <| by exact le_trans ( Multiset.toFinset_card_le _ ) <| Polynomial.card_roots' _;
        rwa [ Finset.card_image_of_injective _ fun x y hxy => by simpa using hxy ] at h_poly_roots_card;
      simp_all +decide [ Polynomial.eval_eq_sum_range ];
      exact lt_of_le_of_lt h_poly_roots_card ( Nat.lt_of_not_ge fun h => hp_deg.not_ge <| by rw [ Polynomial.degree_eq_natDegree <| by aesop_cat ] ; exact_mod_cast h )
    exact absurd h_poly_roots_card (by linarith);
  induction' i with i ih;
  induction' i using Nat.strong_induction_on with i ih;
  have := h_poly_zero i;
  rw [ Finset.sum_eq_single ⟨ i, ih ⟩ ] at this <;> simp_all +decide ;
  intro j hj; cases lt_or_gt_of_ne ( show j.val ≠ i from by simpa [ Fin.ext_iff ] using hj ) <;> [ exact Or.inl ( ih _ ‹_› <| by linarith [ Fin.is_lt j ] ) ; exact Or.inr <| Nat.choose_eq_zero_of_lt ‹_› ] ;);
  refine' ⟨ y, _, hy.2.1, hy.2.2.1, _ ⟩ <;> simp_all +decide [ Finset.prod_range ];
  have h_poly : ∀ j : ℕ, j < r → ∃ c : Fin (j + 1) → ℤ, ∀ i : Fin s, (u i : ℝ) ^ j = ∑ l : Fin (j + 1), (c l : ℝ) * (Nat.choose (u i).toNat l : ℝ) := by
    intro j hj;
    have h_poly : ∀ j : ℕ, ∃ c : Fin (j + 1) → ℤ, ∀ x : ℕ, x ^ j = ∑ l : Fin (j + 1), (c l : ℤ) * Nat.choose x l := by
      intro j;
      induction' j with j ih;
      · exact ⟨ fun l => if l = 0 then 1 else 0, fun x => by simp +decide ⟩;
      · obtain ⟨ c, hc ⟩ := ih;
        have h_expand : ∀ x : ℕ, (x : ℤ) ^ (j + 1) = ∑ l : Fin (j + 1), (c l : ℤ) * (x * Nat.choose x l : ℤ) := by
          simp +decide [ pow_succ', mul_left_comm, Finset.mul_sum _ _ _, hc ];
        have h_identity : ∀ x : ℕ, ∀ l : Fin (j + 1), (x * Nat.choose x l : ℤ) = (l.val + 1) * Nat.choose x (l.val + 1) + l.val * Nat.choose x l := by
          intro x l; norm_cast;
          nlinarith [ Nat.add_one_mul_choose_eq x l, Nat.choose_succ_succ x l ];
        use fun l => ∑ k : Fin (j + 1), c k * (if l.val = k.val + 1 then (k.val + 1 : ℤ) else if l.val = k.val then (k.val : ℤ) else 0);
        intro x; rw [ h_expand x ] ; simp +decide [ h_identity, Finset.sum_mul _ _ _ ] ;
        rw [ Finset.sum_comm ];
        refine' Finset.sum_congr rfl fun i hi => _;
        rw [ Finset.sum_eq_add ( ⟨ i + 1, by linarith [ Fin.is_lt i ] ⟩ : Fin ( j + 2 ) ) ( ⟨ i, by linarith [ Fin.is_lt i ] ⟩ : Fin ( j + 2 ) ) ] <;> norm_num ; ring;
        simp +contextual [ Fin.ext_iff ];
    obtain ⟨ c, hc ⟩ := h_poly j; use c; intro i; specialize hc ( Int.toNat ( u i ) ) ; simp_all +decide [ Int.toNat_of_nonneg ( hu_nonneg i ) ] ;
    exact_mod_cast hc;
  intro k j hj; obtain ⟨ c, hc ⟩ := h_poly j hj; simp +decide [ hc, mul_assoc, mul_left_comm, Finset.mul_sum _ _ _ ] ;
  rw [ Finset.sum_comm ];
  refine' Finset.sum_eq_zero fun l hl => _;
  convert congr_arg ( fun x : ℝ => x * c l ) ( hy.1 k ⟨ l, by linarith [ Fin.is_lt l ] ⟩ ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) <;> ring_nf;
  simp +decide only [mul_assoc, Finset.mul_sum _ _ _, mul_left_comm]