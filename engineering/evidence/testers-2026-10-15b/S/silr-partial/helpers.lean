private noncomputable def SKVProp : Prop := ∀ (r : ℕ), 2 ≤ r → ∀ (s : ℕ), s = 2 * r → ∀ (M : ℝ) (W : ℝ), 1 ≤ W →
    ∀ (u : Fin s → ℤ) (w : Fin s → ℕ), (∀ i, 0 ≤ u i ∧ (u i : ℝ) ≤ M) → StrictMono u →
    (∀ i, 0 < w i) → (∀ i, (w i : ℝ) ≤ W) →
    ∃ v : Fin r → (Fin s → ℤ),
      (∀ (k : Fin r) (j : ℕ), j < r →
        ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧
      (LinearIndependent ℝ (fun k : Fin r => (fun i : Fin s => ((v k i : ℤ) : ℝ)))) ∧
      (Monotone (fun k : Fin r => ∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2)) ∧
      (∏ k : Fin r, (∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2) ≤
        (2 : ℝ) ^ (r * (r - 1)) * (2 * (r : ℝ)) ^ r * W ^ (2 * r) *
        (∏ j ∈ Finset.range r, ((M : ℝ) ^ j / (Nat.factorial j : ℝ))) ^ 2) ∧
      (∀ k : Fin r, ∀ x : Fin s → ℤ,
        (∀ j : ℕ, j < r → ∑ i, (x i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) →
        (fun i : Fin s => (x i : ℝ)) ∉
          Submodule.span ℝ ((fun j : Fin r => fun i : Fin s => (v j i : ℝ)) ''
            { j | j.val < k.val }) →
        ∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2 ≤ ∑ i : Fin s, ((x i : ℤ) : ℝ) ^ 2)

private lemma weighted_vandermonde_trivial_kernel
    (s : ℕ)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_strict : StrictMono u)
    (hw_pos : ∀ i, 0 < w i)
    (a : Fin s → ℤ)
    (ha : ∀ j : ℕ, j < s → ∑ i, (a i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) :
    a = 0 := by
  have h_vandermonde : Matrix.det (Matrix.of (fun i j : Fin s => (w j : ℝ) * (u j : ℝ) ^ (i : ℕ))) ≠ 0 := by
    have h_vandermonde_det : Matrix.det (Matrix.of (fun i j : Fin s => (u j : ℝ) ^ (i : ℕ))) ≠ 0 := by
      erw [ Matrix.det_transpose, Matrix.det_vandermonde ]
      exact Finset.prod_ne_zero_iff.mpr fun i hi => Finset.prod_ne_zero_iff.mpr fun j hj => sub_ne_zero_of_ne <| mod_cast hu_strict.injective.ne <| ne_of_gt <| Finset.mem_Ioi.mp hj
    convert mul_ne_zero h_vandermonde_det ( show ( ∏ i : Fin s, ( w i : ℝ ) ) ≠ 0 from Finset.prod_ne_zero_iff.mpr fun i _ => Nat.cast_ne_zero.mpr <| ne_of_gt <| hw_pos i ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)))
    simp +decide [ Matrix.det_apply', mul_comm, Finset.prod_mul_distrib ]
    simp +decide only [mul_assoc, Finset.mul_sum _ _ _]
  have h_mulvec : Matrix.mulVec (Matrix.of (fun i j : Fin s => (w j : ℝ) * (u j : ℝ) ^ (i : ℕ))) (fun i => (a i : ℝ)) = 0 := by
    ext i; simp_all +decide [ Matrix.mulVec, dotProduct, mul_comm, mul_left_comm ]
  exact funext fun i => by simpa [ funext_iff ] using Matrix.eq_zero_of_mulVec_eq_zero ‹_› h_mulvec |> fun h => by simpa [ funext_iff ] using congr_fun h i

private lemma excess_zero_among_independent
    (r : ℕ) (hr : 2 ≤ r)
    (s : ℕ) (hs : s = 2 * r)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_strict : StrictMono u)
    (hw_pos : ∀ i, 0 < w i)
    (v : Fin r → (Fin s → ℤ))
    (hv_kernel : ∀ (k : Fin r) (j : ℕ), j < r →
      ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0)
    (hv_indep : LinearIndependent ℝ (fun k : Fin r => (fun i : Fin s => ((v k i : ℤ) : ℝ)))) :
    ∃ m : Fin r, ∑ i, (v m i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0 := by
  by_contra h_contra
  push_neg at h_contra
  have h_all_zero : ∀ k : Fin r, ∑ i, ((v k i) : ℝ) * (w i : ℝ) * ((u i) : ℝ) ^ r = 0 := by
    exact h_contra
  have h_contra : r ≤ r - 1 := by
    have h_contra : Module.finrank ℝ (Submodule.span ℝ (Set.range (fun k : Fin r => fun i : Fin s => (v k i : ℝ)))) ≤ Module.finrank ℝ (LinearMap.ker (Matrix.mulVecLin (Matrix.of (fun (j : Fin (r + 1)) (i : Fin s) => (w i : ℝ) * ((u i) : ℝ) ^ (j : ℕ))))) := by
      refine' Submodule.finrank_mono _;
      rw [ Submodule.span_le ];
      rintro _ ⟨ k, rfl ⟩ ; ext j; simp +decide [ Matrix.mulVec, dotProduct, mul_comm, mul_left_comm] ;
      by_cases hj : j.val < r <;> simp_all +decide [ mul_comm];
      rw [ show ( j : ℕ ) = r by linarith [ Fin.is_lt j ] ] ; exact h_contra k;
    have h_contra : Matrix.rank (Matrix.of (fun (j : Fin (r + 1)) (i : Fin s) => (w i : ℝ) * ((u i) : ℝ) ^ (j : ℕ))) = r + 1 := by
      have h_contra : LinearIndependent ℝ (fun j : Fin (r + 1) => fun i : Fin s => (w i : ℝ) * ((u i) : ℝ) ^ (j : ℕ)) := by
        refine' Fintype.linearIndependent_iff.2 _;
        intro g hg i
        have h_poly : ∀ x : ℝ, ∑ j : Fin (r + 1), g j * x ^ (j : ℕ) = 0 := by
          have h_poly : ∀ x : ℝ, ∑ j : Fin (r + 1), g j * x ^ (j : ℕ) = 0 := by
            intro x
            have h_poly_eq : ∀ i : Fin s, ∑ j : Fin (r + 1), g j * (u i : ℝ) ^ (j : ℕ) = 0 := by
              intro i; replace hg := congr_fun hg i; simp_all +decide [ mul_comm ] ;
              simp_all +decide [ ← mul_assoc, ← Finset.sum_mul _ _ _ ];
              exact hg.resolve_right ( ne_of_gt ( hw_pos i ) )
            have h_poly_eq : ∀ p : Polynomial ℝ, p.degree ≤ r → (∀ i : Fin s, p.eval (u i : ℝ) = 0) → p = 0 := by
              intros p hp h_eval_zero
              have h_card_roots : p.roots.toFinset.card ≤ r := by
                exact le_trans ( Multiset.toFinset_card_le _ ) ( le_trans ( Polynomial.card_roots' _ ) ( Polynomial.natDegree_le_of_degree_le hp ) );
              exact Classical.not_not.1 fun h => by have := Finset.card_le_card ( show Finset.image ( fun i : Fin s => ( u i : ℝ ) ) Finset.univ ⊆ p.roots.toFinset from Finset.image_subset_iff.2 fun i _ => by aesop ) ; rw [ Finset.card_image_of_injective _ fun i j hij => by simpa [ hu_strict.injective.eq_iff ] using hij ] at this ; norm_num at this ; linarith;
            specialize h_poly_eq ( ∑ j : Fin ( r + 1 ), g j • Polynomial.X ^ ( j : ℕ ) ) ; simp_all +decide [ Polynomial.eval_finset_sum ];
            replace h_poly_eq := congr_arg ( Polynomial.eval x ) ( h_poly_eq <| le_trans ( Polynomial.degree_sum_le _ _ ) <| Finset.sup_le fun i _ => Polynomial.degree_smul_le _ _ |> le_trans <| Polynomial.degree_X_pow_le _ |> le_trans <| WithBot.coe_le_coe.mpr <| Nat.le_of_lt_succ <| Fin.is_lt i ) ; simp_all +decide [ Polynomial.eval_finset_sum ] ;
          exact h_poly;
        -- Since $\sum_{j=0}^{r} g_j x^j = 0$ for all $x$, the polynomial $\sum_{j=0}^{r} g_j x^j$ is the zero polynomial.
        have h_poly_zero : ∑ j : Fin (r + 1), Polynomial.C (g j) * Polynomial.X ^ (j : ℕ) = 0 := by
          exact Polynomial.funext fun x => by simpa [ Polynomial.eval_finset_sum ] using h_poly x;
        replace h_poly_zero := congr_arg ( fun p => p.coeff ( i : ℕ ) ) h_poly_zero ; simp_all +decide [ Polynomial.coeff_X_pow ] ;
        simp_all +decide [ Fin.val_inj ];
      rw [ ← Matrix.rank_transpose, Matrix.rank ];
      rw [ @LinearMap.finrank_range_of_inj ] <;> norm_num [ Function.Injective ];
      intro a₁ a₂ h; simp_all +decide [ funext_iff, Matrix.vecMul, dotProduct ] ;
      rw [ Fintype.linearIndependent_iff ] at h_contra;
      exact fun i => sub_eq_zero.mp ( h_contra ( fun j => a₁ j - a₂ j ) ( by ext x; simpa [ sub_mul ] using sub_eq_zero.mpr ( h x ) ) i );
    have := LinearMap.finrank_range_add_finrank_ker ( Matrix.mulVecLin ( Matrix.of ( fun ( j : Fin ( r + 1 ) ) ( i : Fin s ) => ( w i : ℝ ) * ( u i : ℝ ) ^ ( j : ℕ ) ) ) ) ; simp_all +decide [ Matrix.rank ] ;
    linarith [ show Module.finrank ℝ ( Submodule.span ℝ ( Set.range fun k i => ( v k i : ℝ ) ) ) = r from by rw [ finrank_span_eq_card ] <;> aesop ]
  linarith [Nat.sub_add_cancel (by linarith : 1 ≤ r)]

private lemma choose_le_pow_div_factorial (n j : ℕ) :
    (Nat.choose n j : ℝ) ≤ (n : ℝ) ^ j / (Nat.factorial j : ℝ) := by
  rw [ le_div_iff₀ ( by positivity ) ];
  rw_mod_cast [ mul_comm, ← Nat.descFactorial_eq_factorial_mul_choose ] ; exact Nat.descFactorial_le_pow n j;

private lemma kernel_binomial_multiply
    (s : ℕ) (u : Fin s → ℤ) (w : Fin s → ℕ) (v : Fin s → ℤ)
    (hu_nonneg : ∀ i, 0 ≤ u i) (ℓ : ℕ) :
    ∀ n : ℕ, (∀ t : ℕ, t < n + ℓ → ∑ i, (v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ t = 0) →
    ∀ j : ℕ, j < n →
      ∑ i, ((Nat.choose (u i).toNat ℓ : ℤ) * v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0 := by
  intro n hn j hj
  induction' ℓ with ℓ ih generalizing n j;
  · aesop;
  · -- Use the identity: (ℓ+1) * choose(n, ℓ+1) = choose(n, ℓ) * (n - ℓ) for natural numbers.
    have h_identity : ∀ i, ((u i).toNat.choose (ℓ + 1) : ℝ) * (ℓ + 1) = ((u i).toNat.choose ℓ : ℝ) * ((u i : ℝ) - ℓ) := by
      intro i; norm_cast; have := Nat.choose_succ_right_eq ( Int.toNat ( u i ) ) ℓ; simp_all +decide [add_comm] ;
      by_cases h : ℓ ≤ Int.toNat ( u i ) <;> simp_all +decide [ Nat.choose_eq_zero_of_lt ];
    -- Apply the identity to rewrite the sum.
    have h_sum_rewrite : ∑ i, ((u i).toNat.choose (ℓ + 1) : ℝ) * (v i : ℝ) * (w i : ℝ) * (u i : ℝ) ^ j * (ℓ + 1) = ∑ i, ((u i).toNat.choose ℓ : ℝ) * (v i : ℝ) * (w i : ℝ) * (u i : ℝ) ^ (j + 1) - ℓ * ∑ i, ((u i).toNat.choose ℓ : ℝ) * (v i : ℝ) * (w i : ℝ) * (u i : ℝ) ^ j := by
      rw [ Finset.mul_sum _ _ _ ] ; rw [ ← Finset.sum_sub_distrib ] ; congr ; ext i ; linear_combination' h_identity i * v i * w i * u i ^ j;
    simp_all +decide [ ← Finset.sum_mul _ _ _ ];
    exact eq_zero_of_ne_zero_of_mul_right_eq_zero ( by positivity ) ( h_sum_rewrite.trans ( by rw [ ih ( n + 1 ) ( fun t ht => hn t ( by linarith ) ) ( j + 1 ) ( by linarith ), ih n ( fun t ht => hn t ( by linarith ) ) j hj ] ; ring ) )

private lemma binomial_multiply_norm_bound
    (s : ℕ) (M : ℝ) (u : Fin s → ℤ) (v : Fin s → ℤ) (ℓ : ℕ)
    (hu_range : ∀ i, 0 ≤ u i ∧ (u i : ℝ) ≤ M) :
    ∑ i : Fin s, ((Nat.choose (u i).toNat ℓ : ℤ) * v i : ℝ) ^ 2 ≤
      (M ^ ℓ / (Nat.factorial ℓ : ℝ)) ^ 2 * ∑ i : Fin s, ((v i : ℤ) : ℝ) ^ 2 := by
  -- By the properties of binomial coefficients and the given bounds on $u_i$, we have $\binom{u_i}{\ell} \leq \frac{M^\ell}{\ell!}$.
  have h_binom_bound : ∀ i, ((Nat.choose (u i).toNat ℓ) : ℝ) ≤ (M ^ ℓ / (Nat.factorial ℓ)) := by
    intro i
    have h_choose_bound : (Nat.choose (u i).toNat ℓ : ℝ) ≤ (↑(u i).toNat) ^ ℓ / (Nat.factorial ℓ) := by
      convert choose_le_pow_div_factorial ( Int.toNat ( u i ) ) ℓ using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
    refine le_trans h_choose_bound ?_;
    gcongr;
    exact le_trans ( mod_cast Int.toNat_of_nonneg ( hu_range i |>.1 ) |> le_of_eq ) ( hu_range i |>.2 );
  rw [ Finset.mul_sum _ _ _ ] ; exact Finset.sum_le_sum fun i _ => by simpa [ mul_pow ] using mul_le_mul_of_nonneg_right ( pow_le_pow_left₀ ( Nat.cast_nonneg _ ) ( h_binom_bound i ) 2 ) ( sq_nonneg _ ) ;

private lemma pow_div_factorial_mono {M : ℝ} (hM : 0 ≤ M) {j k : ℕ}
    (hjk : j ≤ k) (hkM : (k : ℝ) ≤ M) :
    M ^ j / (Nat.factorial j : ℝ) ≤ M ^ k / (Nat.factorial k : ℝ) := by
  induction hjk <;> simp_all +decide [ Nat.factorial_succ, pow_succ ];
  rename_i k hk ih;
  exact le_trans ( ih ( by linarith ) ) ( by rw [ div_le_div_iff₀ ] <;> first | positivity | nlinarith [ pow_nonneg hM k, show ( k.factorial : ℝ ) > 0 by positivity, mul_le_mul_of_nonneg_right hkM ( show ( 0 : ℝ ) ≤ M ^ k by positivity ) ] )

private lemma kernel_high_excess_count
    (r s e : ℕ) (hs : s = 2 * r) (he : e ≤ r)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_strict : StrictMono u) (hw_pos : ∀ i, 0 < w i)
    (t : ℕ) (v : Fin t → (Fin s → ℤ))
    (hv : ∀ (k : Fin t) (j : ℕ), j < r + e →
      ∑ i, (v k i : ℝ) * (w i : ℝ) * (u i : ℝ) ^ j = 0)
    (hv_indep : LinearIndependent ℝ (fun k : Fin t => fun i : Fin s => (v k i : ℝ))) :
    t ≤ r - e := by
  -- By the Vandermonde argument, the (r+e) × s matrix A with A(j,i) = w_i * u_i^j has rank r+e.
  have h_rank : Matrix.rank (Matrix.of (fun (j : Fin (r + e)) (i : Fin s) => (w i : ℝ) * ((u i : ℝ)) ^ j.val)) = r + e := by
    -- The rows of the matrix are linearly independent because the Vandermonde matrix with distinct nodes is invertible.
    have h_vandermonde_indep : LinearIndependent ℝ (fun j : Fin (r + e) => fun i : Fin s => (w i : ℝ) * ((u i : ℝ)) ^ j.val) := by
      refine' Fintype.linearIndependent_iff.2 _;
      intro g hg i
      have h_poly : ∀ i_1 : Fin s, ∑ j : Fin (r + e), g j * ((u i_1 : ℝ)) ^ (j : ℕ) = 0 := by
        intro i_1; replace hg := congr_fun hg i_1; simp_all +decide ;
        convert congr_arg ( fun x : ℝ => x / ( w i_1 : ℝ ) ) hg using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) <;> norm_num [ Finset.sum_div _ _ _, mul_assoc, mul_comm, mul_left_comm, ne_of_gt ( hw_pos i_1 ) ];
        exact Finset.sum_congr rfl fun _ _ => by rw [ mul_div_assoc, mul_div_cancel_right₀ _ ( Nat.cast_ne_zero.mpr <| ne_of_gt <| hw_pos i_1 ) ] ;
      -- Since $u$ is strictly monotone, the polynomial $\sum_{j=0}^{r+e-1} g_j x^j$ has $s$ distinct roots, which implies it is the zero polynomial.
      have h_poly_zero : ∑ j : Fin (r + e), g j • (Polynomial.monomial j.val (1 : ℝ)) = 0 := by
        refine' Polynomial.eq_of_degree_sub_lt_of_eval_finset_eq _ _ _;
        exact Finset.image ( fun i : Fin s => ( u i : ℝ ) ) Finset.univ;
        · rw [ Finset.card_image_of_injective _ fun i j hij => hu_strict.injective <| by simpa using hij ] ; norm_num [ Polynomial.degree_lt_iff_coeff_zero ];
          simp +decide [ Polynomial.coeff_monomial ];
          exact fun m hm => Finset.sum_eq_zero fun i hi => if_neg <| by linarith [ Fin.is_lt i ] ;
        · simp_all +decide [ Polynomial.eval_finset_sum ];
      replace h_poly_zero := congr_arg ( fun p => p.coeff i ) h_poly_zero ; simp_all +decide [ Polynomial.coeff_monomial ];
      simp_all +decide [ Fin.val_inj ];
    rw [Matrix.rank_eq_finrank_span_row]
    exact (finrank_span_eq_card h_vandermonde_indep).trans (Fintype.card_fin _)
  have h_ker_dim : Module.finrank ℝ (LinearMap.ker (Matrix.mulVecLin (Matrix.of (fun (j : Fin (r + e)) (i : Fin s) => (w i : ℝ) * ((u i : ℝ)) ^ j.val)))) = s - (r + e) := by
    have := LinearMap.finrank_range_add_finrank_ker ( Matrix.mulVecLin ( Matrix.of ( fun ( j : Fin ( r + e ) ) ( i : Fin s ) => ( w i : ℝ ) * ( u i : ℝ ) ^ j.val ) ) );
    have hr' : Module.finrank ℝ (LinearMap.range (Matrix.mulVecLin (Matrix.of (fun (j : Fin (r + e)) (i : Fin s) => (w i : ℝ) * ((u i : ℝ)) ^ j.val)))) = r + e := h_rank
    rw [hr', Module.finrank_fin_fun] at this
    omega
  -- Since the vectors $v_k$ lie in the kernel of $A$, their span is a subspace of the kernel.
  have h_span_ker : Submodule.span ℝ (Set.range (fun k : Fin t => (fun i : Fin s => ((v k i : ℤ) : ℝ)))) ≤ LinearMap.ker (Matrix.mulVecLin (Matrix.of (fun (j : Fin (r + e)) (i : Fin s) => (w i : ℝ) * ((u i : ℝ)) ^ j.val))) := by
    rw [ Submodule.span_le ];
    rintro _ ⟨ k, rfl ⟩ ; ext j; simp +decide [ Matrix.mulVec, dotProduct, mul_comm, mul_left_comm ] ;
    simpa only [ mul_assoc, mul_comm, mul_left_comm ] using hv k j ( Fin.is_lt j );
  have := Submodule.finrank_mono h_span_ker;
  rw [ finrank_span_eq_card ] at this <;> norm_num [ hv_indep ] at * ; omega

private lemma binomial_multiply_moment
    (s : ℕ) (u : Fin s → ℤ) (w : Fin s → ℕ) (v : Fin s → ℤ)
    (hu_nonneg : ∀ i, 0 ≤ u i) (e : ℕ) :
    ∀ r : ℕ,
    (∀ t : ℕ, t < r + e → ∑ i, (v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ t = 0) →
    (∑ i, (v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ (r + e) ≠ 0) →
    ∑ i, ((Nat.choose (u i).toNat e : ℤ) * v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0 := by
  induction' e with e ih;
  · aesop;
  · intro r hr₁ hr₂;
    have h_identity : ∑ i, (Nat.choose (u i).toNat (e + 1) * v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r = (1 / (e + 1 : ℝ)) * (∑ i, (Nat.choose (u i).toNat e * v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ (r + 1)) - (e / (e + 1 : ℝ)) * (∑ i, (Nat.choose (u i).toNat e * v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r) := by
      have h_identity : ∀ i, (Nat.choose (u i).toNat (e + 1) : ℝ) = (Nat.choose (u i).toNat e : ℝ) * ((u i : ℝ) - e) / (e + 1) := by
        intro i; rw [ eq_div_iff ] <;> norm_cast ;
        cases h : u i <;> simp_all +decide [ Nat.choose_succ_right_eq ];
        · exact Classical.or_iff_not_imp_right.2 fun h' => by rw [ Nat.cast_sub ( le_of_not_gt fun h'' => h' <| Nat.choose_eq_zero_of_lt h'' ) ] ;
        · linarith [ hu_nonneg i, Int.negSucc_lt_zero ‹_› ];
      rw [ Finset.mul_sum _ _ _, Finset.mul_sum _ _ _ ] ; rw [ ← Finset.sum_sub_distrib ] ; congr ; ext i ; rw [ h_identity i ] ; ring;
    have h_ind : ∑ i, (Nat.choose (u i).toNat e * v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ (r + 1) ≠ 0 := by
      apply ih (r + 1);
      · exact fun t ht => hr₁ t ( by linarith );
      · convert hr₂ using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; ring_nf;
    have h_ind : ∑ i, (Nat.choose (u i).toNat e * v i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r = 0 := by
      convert kernel_binomial_multiply s u w v hu_nonneg e ( r + 1 ) ( fun t ht => hr₁ t ( by linarith ) ) r ( by linarith ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
    simp_all +decide [ Nat.cast_add_one_ne_zero ]

private lemma excess_product_bound
    (r : ℕ) (hr : 2 ≤ r)
    (m : ℕ) (hm : m ≤ r)
    (M : ℝ) (hM : 0 ≤ M) (hrM : (r : ℝ) - 1 ≤ M)
    (e : Fin m → ℕ)
    (he_pos : ∀ k, 1 ≤ e k)
    (he_bound : ∀ k, e k ≤ r - 1)
    -- Dimension constraint: for each e₀ ≥ 1, at most r-e₀ indices have excess ≥ e₀
    (he_dim : ∀ e₀ : ℕ, 1 ≤ e₀ →
      (Finset.univ.filter (fun k : Fin m => e₀ ≤ e k)).card ≤ r - e₀) :
    ∏ k : Fin m, (M ^ (e k) / (Nat.factorial (e k) : ℝ)) ≤
      ∏ j ∈ Finset.range r, (M ^ j / (Nat.factorial j : ℝ)) := by
  -- By sorting the excesses, we can apply the induction hypothesis.
  have h_sorted : ∃ σ : Fin m ≃ Fin m, ∀ k l : Fin m, k < l → e (σ k) ≤ e (σ l) := by
    have h_sort : ∃ σ : Fin m → Fin m, Function.Injective σ ∧ ∀ k l : Fin m, k < l → e (σ k) ≤ e (σ l) := by
      have h_exists_min : ∀ (S : Finset (Fin m)), S.Nonempty → ∃ k ∈ S, ∀ j ∈ S, e k ≤ e j := by
        exact fun S hS => Finset.exists_min_image _ _ hS
      have h_sort : ∀ (n : ℕ) (hn : n ≤ m), ∀ (S : Finset (Fin m)), S.card = n → ∃ σ : Fin n → Fin m, Function.Injective σ ∧ (∀ k : Fin n, σ k ∈ S) ∧ (∀ k l : Fin n, k < l → e (σ k) ≤ e (σ l)) := by
        intro n hn S hS_card
        induction' n with n ih generalizing S;
        · simp +decide [ Function.Injective ];
        · obtain ⟨ k, hk₁, hk₂ ⟩ := h_exists_min S ( Finset.card_pos.mp ( by linarith ) ) ; obtain ⟨ σ, hσ₁, hσ₂, hσ₃ ⟩ := ih ( by linarith ) ( S.erase k ) ( by rw [ Finset.card_erase_of_mem hk₁, hS_card ] ; simp +decide ) ; use Fin.cons k σ; simp_all +decide [ Fin.forall_fin_succ, Function.Injective ] ;
          exact ⟨ fun i hi => False.elim <| hσ₂ i |>.1 <| hi.symm, fun i j hij => hσ₁ hij ⟩;
      exact Exists.elim ( h_sort m le_rfl Finset.univ ( by simp ) ) fun σ hσ => ⟨ σ, hσ.1, hσ.2.2 ⟩;
    exact ⟨ Equiv.ofBijective h_sort.choose ( ⟨ h_sort.choose_spec.1, Finite.injective_iff_surjective.mp h_sort.choose_spec.1 ⟩ ), h_sort.choose_spec.2 ⟩;
  obtain ⟨σ, hσ⟩ := h_sorted
  have h_prod_sorted : ∏ k, M ^ (e (σ k)) / (Nat.factorial (e (σ k)) : ℝ) ≤ ∏ j ∈ Finset.range m, M ^ (r - m + j) / (Nat.factorial (r - m + j) : ℝ) := by
    have h_prod_sorted : ∀ k : Fin m, e (σ k) ≤ r - m + k := by
      intro k
      have h_card : Finset.card (Finset.filter (fun l => e (σ k) ≤ e (σ l)) Finset.univ) ≥ m - k := by
        refine' le_trans _ ( Finset.card_mono <| show Finset.image ( fun l : Fin m => l ) ( Finset.Ici k ) ⊆ Finset.filter ( fun l => e ( σ k ) ≤ e ( σ l ) ) Finset.univ from _ );
        · simp +decide ;
        · grind;
      have h_card : Finset.card (Finset.filter (fun l => e (σ k) ≤ e l) Finset.univ) ≥ m - k := by
        convert h_card using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
        rw [ Finset.card_filter, Finset.card_filter ];
        conv_lhs => rw [ ← Equiv.sum_comp σ ] ;
      grind +suggestions;
    have h_prod_sorted : ∀ k : Fin m, M ^ (e (σ k)) / (Nat.factorial (e (σ k)) : ℝ) ≤ M ^ (r - m + k) / (Nat.factorial (r - m + k) : ℝ) := by
      intros k
      apply pow_div_factorial_mono hM (h_prod_sorted k);
      rw [ Nat.cast_add, Nat.cast_sub hm ] ; linarith [ show ( k : ℝ ) + 1 ≤ m by norm_cast; linarith [ Fin.is_lt k ] ];
    simpa only [ Finset.prod_range ] using Finset.prod_le_prod ( fun _ _ => div_nonneg ( pow_nonneg hM _ ) ( Nat.cast_nonneg _ ) ) fun _ _ => h_prod_sorted _;
  have h_prod_split : ∏ j ∈ Finset.range r, M ^ j / (Nat.factorial j : ℝ) = (∏ j ∈ Finset.range (r - m), M ^ j / (Nat.factorial j : ℝ)) * (∏ j ∈ Finset.range m, M ^ (r - m + j) / (Nat.factorial (r - m + j) : ℝ)) := by
    convert Finset.prod_range_add _ _ _ using 3 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; omega;
  have h_prod_ge_one : ∀ j ∈ Finset.range (r - m), 1 ≤ M ^ j / (Nat.factorial j : ℝ) := by
    intros j hj; rw [ one_le_div ( by positivity ) ] ; induction' j with j ih <;> norm_num [ pow_succ, Nat.factorial_succ ] at *;
    nlinarith [ ih ( Nat.lt_of_succ_lt hj ), show ( j : ℝ ) + 1 ≤ r - 1 by exact le_tsub_of_add_le_right ( by norm_cast; omega ), pow_nonneg hM j ];
  rw [ ← Equiv.prod_comp σ ];
  exact h_prod_sorted.trans ( h_prod_split.symm ▸ le_mul_of_one_le_left ( Finset.prod_nonneg fun _ _ => div_nonneg ( pow_nonneg hM _ ) ( Nat.cast_nonneg _ ) ) ( le_trans ( by norm_num ) ( Finset.prod_le_prod ( fun _ _ => by positivity ) h_prod_ge_one ) ) )

private lemma comparison_with_vanishing
    (r : ℕ) (hr : 2 ≤ r)
    (s : ℕ) (hs : s = 2 * r)
    (M : ℝ) (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_range : ∀ i, 0 ≤ u i ∧ (u i : ℝ) ≤ M)
    (hu_strict : StrictMono u) (hw_pos : ∀ i, 0 < w i)
    (v : Fin r → (Fin s → ℤ))
    (hv_kernel : ∀ (k : Fin r) (j : ℕ), j < r →
      ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0)
    (hv_indep : LinearIndependent ℝ (fun k : Fin r => (fun i : Fin s => ((v k i : ℤ) : ℝ))))
    (hv_succ : ∀ k : Fin r, ∀ x : Fin s → ℤ,
      (∀ j : ℕ, j < r → ∑ i, (x i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) →
      (fun i : Fin s => (x i : ℝ)) ∉
        Submodule.span ℝ ((fun j : Fin r => fun i : Fin s => (v j i : ℝ)) ''
          { j | j.val < k.val }) →
      ∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2 ≤ ∑ i : Fin s, ((x i : ℤ) : ℝ) ^ 2)
    (m : Fin r)
    (hm_nonzero : ∑ i, (v m i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0)
    (hm_min : ∀ k : Fin r, k.val < m.val →
      ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r = 0)
    (k : Fin r) (hk : k.val < m.val) :
    ∃ e : ℕ, 1 ≤ e ∧ e ≤ r - 1 ∧
      (∀ j : ℕ, j < r + e → ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧
      ∑ i : Fin s, ((v m i : ℤ) : ℝ) ^ 2 ≤
        (M ^ e / (Nat.factorial e : ℝ)) ^ 2 *
        ∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2 := by
  obtain ⟨e, he_pos, he_bound, he_vanish⟩ : ∃ e : ℕ, 1 ≤ e ∧ e ≤ r - 1 ∧ (∀ j : ℕ, j < r + e → ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧ (∑ i, ((Nat.choose (u i).toNat e : ℤ) * v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0) := by
    -- Let $t$ be the smallest index such that $L_t(v_k) \neq 0$.
    obtain ⟨t, ht⟩ : ∃ t : ℕ, r < t ∧ t < s ∧ (∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ t ≠ 0) ∧ (∀ j : ℕ, r < j → j < t → (∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0)) := by
      have ht_exists : ∃ t, r < t ∧ t < s ∧ (∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ t ≠ 0) := by
        have ht_exists : ∃ t, t < s ∧ (∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ t ≠ 0) := by
          contrapose! hv_indep;
          have := weighted_vandermonde_trivial_kernel s u w hu_strict hw_pos ( v k ) hv_indep; simp_all +decide [ funext_iff ] ;
          exact fun h => by have := h.ne_zero k; simp_all +decide [ funext_iff ] ;
        obtain ⟨ t, ht₁, ht₂ ⟩ := ht_exists;
        by_cases ht₃ : t < r;
        · exact False.elim <| ht₂ <| hv_kernel k t ht₃;
        · exact ⟨ t, lt_of_le_of_ne ( le_of_not_gt ht₃ ) ( Ne.symm <| by rintro rfl; exact ht₂ <| hm_min k hk ), ht₁, ht₂ ⟩;
      exact ⟨ Nat.find ht_exists, Nat.find_spec ht_exists |>.1, Nat.find_spec ht_exists |>.2.1, Nat.find_spec ht_exists |>.2.2, fun j hj₁ hj₂ => Classical.not_not.1 fun hj₃ => Nat.find_min ht_exists hj₂ ⟨ hj₁, by linarith [ Nat.find_spec ht_exists |>.2.1 ], hj₃ ⟩ ⟩;
    refine' ⟨ t - r, _, _, _, _ ⟩ <;> norm_num at *;
    · exact Nat.sub_pos_of_lt ht.1;
    · omega;
    · intro j hj; by_cases hj' : j < r <;> simp_all +decide [ Nat.add_sub_of_le ht.1.le ] ;
      cases hj'.eq_or_lt <;> [ aesop; exact ht.2.2.2 _ ‹_› ‹_› ];
    · convert binomial_multiply_moment s u w ( v k ) ( fun i => hu_range i |>.1 ) ( t - r ) r _ _ using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
      · intro j hj; by_cases hj' : j < r <;> simp_all +decide [ Nat.add_sub_of_le ht.1.le ] ;
        cases hj'.eq_or_lt <;> [ aesop; exact ht.2.2.2 _ ‹_› ‹_› ];
      · simpa only [ add_tsub_cancel_of_le ht.1.le ] using ht.2.2.1;
  refine' ⟨ e, he_pos, he_bound, he_vanish.1, le_trans ( hv_succ m _ _ _ ) _ ⟩;
  use fun i => Nat.choose ( u i |> Int.toNat ) e * v k i;
  · convert kernel_binomial_multiply s u w ( v k ) ( fun i => hu_range i |>.1 ) e r ( fun j hj => he_vanish.1 j ( by linarith ) ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
    norm_cast;
  · intro h;
    refine' he_vanish.2 _;
    rw [ Submodule.mem_span ] at h;
    specialize h ( LinearMap.ker ( show ( Fin s → ℝ ) →ₗ[ℝ] ℝ from { toFun := fun x => ∑ i, x i * ( w i : ℝ ) * ( u i : ℝ ) ^ r, map_add' := fun x y => by simp +decide [ Finset.sum_add_distrib, mul_add, add_mul, mul_comm, mul_left_comm ], map_smul' := fun c x => by simp +decide [ Finset.mul_sum _ _ _, mul_assoc, mul_comm, mul_left_comm ] } ) ) ; simp_all +decide [ Set.subset_def ];
  · convert binomial_multiply_norm_bound s M u ( v k ) e hu_range using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
    norm_cast

private lemma dim_constraint_from_vanishing
    (r s : ℕ) (_hr : 2 ≤ r) (hs : s = 2 * r)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_strict : StrictMono u) (hw_pos : ∀ i, 0 < w i)
    (m : ℕ) (_hm : m ≤ r)
    (v : Fin m → (Fin s → ℤ))
    (hv_indep : LinearIndependent ℝ (fun k : Fin m => fun i : Fin s => (v k i : ℝ)))
    (e : Fin m → ℕ)
    (he_vanish : ∀ k : Fin m, ∀ j : ℕ, j < r + e k →
      ∑ i, (v k i : ℝ) * (w i : ℝ) * (u i : ℝ) ^ j = 0) :
    ∀ e₀ : ℕ, 1 ≤ e₀ →
      (Finset.univ.filter (fun k : Fin m => e₀ ≤ e k)).card ≤ r - e₀ := by
  intro e₀ he₀_pos;
  by_cases he₀_le_r : e₀ ≤ r;
  · convert kernel_high_excess_count r s e₀ hs he₀_le_r u w hu_strict hw_pos _ _ _ _;
    use fun k i => v ( Finset.orderEmbOfFin ( Finset.univ.filter fun k => e₀ ≤ e k ) ( by simp +decide ) k ) i;
    · exact fun k j hj => he_vanish _ _ <| by linarith [ Finset.mem_filter.mp ( Finset.orderEmbOfFin_mem ( Finset.univ.filter fun k => e₀ ≤ e k ) ( by simp +decide ) k ) ] ;
    · exact hv_indep.comp _ ( fun k l hkl => by simpa [ Fin.ext_iff ] using hkl );
  · have h_empty : ∀ k : Fin m, e k < r := by
      intro k;
      contrapose! hv_indep;
      have h_zero : ∀ i : Fin s, v k i = 0 := by
        have h_zero : ∀ j : ℕ, j < s → ∑ i, (v k i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0 := by
          exact fun j hj => he_vanish k j ( by linarith );
        have := weighted_vandermonde_trivial_kernel s u w hu_strict hw_pos ( v k ) h_zero; aesop;
      rw [ Fintype.not_linearIndependent_iff ];
      exact ⟨ fun i => if i = k then 1 else 0, by aesop ⟩;
    exact Finset.card_eq_zero.mpr ( Finset.eq_empty_of_forall_notMem fun k hk => by linarith [ Finset.mem_filter.mp hk, h_empty k ] ) |> fun h => h.symm ▸ Nat.zero_le _

private lemma multiply_comparison_bounds
    (r : ℕ)
    (N : Fin r → ℝ) (hN_nonneg : ∀ k, 0 ≤ N k)
    (N_mono : Monotone N)
    (m : Fin r)
    (f : Fin m.val → ℝ) (hf_nonneg : ∀ k, 0 ≤ f k)
    (h_comp : ∀ k : Fin m.val, N m ≤ f k * N ⟨k.val, by omega⟩)
    : N m ^ r ≤ (∏ k : Fin m.val, f k) * ∏ k : Fin r, N k := by
  have h_prod_mono : N m ^ (r - m.val) ≤ ∏ k : Fin (r - m.val), N (⟨m.val + k.val, by
    linarith [ Fin.is_lt m, Fin.is_lt k, Nat.sub_add_cancel ( show ( m : ℕ ) ≤ r from m.2.le ) ]⟩) := by
    exact le_trans ( by norm_num ) ( Finset.prod_le_prod ( fun _ _ => hN_nonneg _ ) fun _ _ => N_mono <| Fin.le_iff_val_le_val.mpr <| Nat.le_add_right _ _ )
  generalize_proofs at *;
  convert mul_le_mul ( show N m ^ m.val ≤ ∏ k : Fin m, f k * N ⟨ k.val, by linarith [ Fin.is_lt k, m.2 ] ⟩ from ?_ ) h_prod_mono ( ?_ ) ( Finset.prod_nonneg fun _ _ => mul_nonneg ( hf_nonneg _ ) ( hN_nonneg _ ) ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
  · rw [ ← pow_add, Nat.add_sub_of_le ( Nat.le_of_lt m.2 ) ];
  · rw [ Finset.prod_mul_distrib ];
    rw [ mul_assoc, ← Finset.prod_image ];
    · rw [ ← Finset.prod_mul_prod_compl ];
      congr! 2;
      any_goals exact Finset.univ.filter fun i => i.val < m.val;
      · refine' Finset.prod_bij ( fun x hx => ⟨ x, by linarith [ Fin.is_lt x, Fin.is_lt m, Finset.mem_filter.mp hx ] ⟩ ) _ _ _ _ <;> simp +decide [ Fin.ext_iff ];
        exact fun k => ⟨ ⟨ k, by linarith [ Fin.is_lt k, Fin.is_lt m ] ⟩, k.2, rfl ⟩;
      · refine' Finset.prod_bij ( fun i hi => ⟨ i - m, by
          grind ⟩ ) _ _ _ _ <;> simp +decide [Fin.ext_iff]
        all_goals generalize_proofs at *;
        · grind;
        · exact fun k => ⟨ ⟨ m + k, by linarith [ Fin.is_lt k, Nat.sub_add_cancel ( show ( m : ℕ ) ≤ r from m.2.le ) ] ⟩, Nat.le_add_right _ _, by simp +decide ⟩;
        · exact fun a ha => congr_arg N ( Fin.ext <| by simp +decide [ Nat.add_sub_of_le <| show ( m : ℕ ) ≤ a from ha ] );
    · exact fun x _ y _ h => by simpa [ Fin.ext_iff ] using h;
  · exact le_trans ( by norm_num ) ( Finset.prod_le_prod ( fun _ _ => hN_nonneg _ ) fun _ _ => h_comp _ );
  · exact pow_nonneg ( hN_nonneg _ ) _

private lemma excess_zero_with_comparison_bound
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
    -- Successive minima property
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

private lemma lattice_core
    (r : ℕ) (hr : 2 ≤ r) (hSKV : SKVProp)
    (s : ℕ) (hs : s = 2 * r)
    (M : ℝ) (hM : (s : ℝ) - 1 ≤ M)
    (W : ℝ) (hW : 1 ≤ W)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_range : ∀ i, 0 ≤ u i ∧ (u i : ℝ) ≤ M)
    (hu_strict : StrictMono u)
    (hw_pos : ∀ i, 0 < w i)
    (hw_bound : ∀ i, (w i : ℝ) ≤ W) :
    ∃ a : Fin s → ℤ,
      (∀ (j : ℕ), j < r → ∑ i, (a i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧
      (∑ i, (a i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0) ∧
      ((∑ i : Fin s, ((a i : ℤ) : ℝ) ^ 2) ^ r ≤
        (∏ j ∈ Finset.range r, ((M : ℝ) ^ j / (Nat.factorial j : ℝ))) ^ 4 *
        (2 : ℝ) ^ (r * (r - 1)) * (2 * (r : ℝ)) ^ r * W ^ (2 * r)) := by
  obtain ⟨v, hv_kernel, hv_indep, hv_mono, hv_prod, hv_succ⟩ :=
    hSKV r hr s hs M W hW u w hu_range hu_strict hw_pos hw_bound
  obtain ⟨m, hm_nonzero, hm_bound⟩ :=
    excess_zero_with_comparison_bound r hr s hs M hM u w hu_range hu_strict hw_pos
      v hv_kernel hv_indep hv_mono hv_succ
  refine ⟨v m, fun j hj => hv_kernel m j hj, hm_nonzero, ?_⟩
  set P := ∏ j ∈ Finset.range r, ((M : ℝ) ^ j / (Nat.factorial j : ℝ))
  set Q := (2 : ℝ) ^ (r * (r - 1)) * (2 * (r : ℝ)) ^ r * W ^ (2 * r)
  calc (∑ i : Fin s, ((v m i : ℤ) : ℝ) ^ 2) ^ r
      ≤ P ^ 2 * ∏ k : Fin r, (∑ i : Fin s, ((v k i : ℤ) : ℝ) ^ 2) := hm_bound
    _ ≤ P ^ 2 * (Q * P ^ 2) := by
        gcongr
    _ = P ^ 4 * Q := by ring
    _ = P ^ 4 * (2 : ℝ) ^ (r * (r - 1)) * (2 * (r : ℝ)) ^ r * W ^ (2 * r) := by ring

private lemma factorial_product_lower_bound (r : ℕ) (hr : 2 ≤ r) :
    ((r : ℝ) / 64) ^ (r * (r - 1) / 2) ≤
    ∏ j ∈ Finset.range r, (Nat.factorial j : ℝ) := by
  induction' r with r ih <;> norm_num [ Finset.prod_range_succ ] at *;
  by_cases hr : r ≤ 64;
  · interval_cases r <;> norm_num [ Nat.factorial_succ, Finset.prod_range_succ ]
    all_goals first
      | (rw [show (2080 : ℕ) = 32 * 65 by norm_num, pow_mul]
         exact le_trans (pow_le_pow_left₀ (by norm_num) (show ((65 : ℝ) / 64) ^ 32 ≤ 3 by norm_num) 65) (by norm_num))
      | exact le_trans (pow_le_one₀ (by norm_num) (by norm_num)) (by norm_num)
  · -- For the inductive step, we can use the fact that $r! \geq \left(\frac{r}{e}\right)^r$.
    have h_factorial_bound : (r.factorial : ℝ) ≥ (r / Real.exp 1) ^ r := by
      rw [ div_pow, ge_iff_le, div_le_iff₀ ] <;> norm_cast <;> norm_num [ Nat.factorial_pos ];
      · rw [ ← div_le_iff₀' ( by positivity ) ] ; rw [ Real.exp_eq_exp_ℝ ] ; norm_num [ NormedSpace.exp_eq_tsum_div ] ; exact Summable.le_tsum ( show Summable _ from Real.summable_pow_div_factorial _ ) r ( fun _ _ => by positivity ) ;
      · positivity;
    -- We can divide both sides by $(r / 64)^{r(r-1)/2}$ to simplify the inequality.
    suffices h_div : ((r + 1) / r : ℝ) ^ (r * (r - 1) / 2) * ((r + 1) / 64 : ℝ) ^ r ≤ (r / Real.exp 1) ^ r by
      refine le_trans ?_ ( mul_le_mul ( ih <| by linarith ) h_factorial_bound ?_ ?_ ) <;> try positivity;
      convert mul_le_mul_of_nonneg_left h_div ( show ( 0 :ℝ ) ≤ ( r / 64 ) ^ ( r * ( r - 1 ) / 2 ) by positivity ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
      rw [ ← mul_assoc, ← mul_pow ];
      rw [ show ( r + 1 ) * r / 2 = r * ( r - 1 ) / 2 + r by exact Nat.div_eq_of_eq_mul_left zero_lt_two <| by nlinarith [ Nat.sub_add_cancel ( by linarith : 1 ≤ r ), Nat.div_mul_cancel ( show 2 ∣ r * ( r - 1 ) from even_iff_two_dvd.mp <| Nat.even_mul_pred_self _ ) ] ] ; rw [ pow_add ] ; ring_nf;
      norm_num [ sq, mul_assoc, ne_of_gt ( by linarith : 0 < r ) ];
    -- We can simplify the inequality by taking the $r$-th root of both sides.
    suffices h_root : ((r + 1) / r : ℝ) ^ ((r - 1) / 2 : ℝ) * ((r + 1) / 64 : ℝ) ≤ (r / Real.exp 1) by
      convert pow_le_pow_left₀ ( by positivity ) h_root r using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; norm_num [ mul_pow, ← Real.rpow_natCast, ← Real.rpow_mul ( by positivity : 0 ≤ ( r + 1 : ℝ ) / r ) ] ; ring_nf ; norm_num [ Nat.cast_sub ( show 1 ≤ r by linarith ) ] ; ring_nf;
      exact Or.inl ( by rw [ ← Real.rpow_natCast ] ; rw [ Nat.cast_div ( show 2 ∣ r * ( r - 1 ) from even_iff_two_dvd.mp ( Nat.even_mul_pred_self _ ) ) ( by positivity ) ] ; cases r <;> norm_num ; ring_nf ) ;
    -- We'll use that $(1 + \frac{1}{r})^{(r-1)/2} \leq e^{1/2}$ for $r \geq 65$.
    have h_exp_bound : ((r + 1) / r : ℝ) ^ ((r - 1) / 2 : ℝ) ≤ Real.exp (1 / 2) := by
      rw [ Real.rpow_def_of_pos ( by exact div_pos ( by positivity ) ( by norm_cast; linarith ) ) ];
      norm_num +zetaDelta at *;
      exact le_trans ( mul_le_mul_of_nonneg_right ( Real.log_le_sub_one_of_pos ( by positivity ) ) ( by linarith [ show ( r : ℝ ) ≥ 65 by norm_cast ] ) ) ( by nlinarith [ show ( r : ℝ ) ≥ 65 by norm_cast, div_mul_cancel₀ ( ( r : ℝ ) + 1 ) ( by positivity : ( r : ℝ ) ≠ 0 ) ] );
    refine le_trans ( mul_le_mul_of_nonneg_right h_exp_bound <| by positivity ) ?_;
    rw [ le_div_iff₀ ( Real.exp_pos _ ) ];
    have := Real.exp_one_lt_d9.le ; norm_num1 at * ; rw [ show ( 1 : ℝ ) = 1 / 2 + 1 / 2 by norm_num, Real.exp_add ] at * ; norm_num at *;
    nlinarith [ Real.add_one_le_exp ( 1 / 2 ), show ( r : ℝ ) ≥ 65 by norm_cast, mul_le_mul_of_nonneg_left ( show ( r : ℝ ) ≥ 65 by norm_cast ) ( Real.exp_nonneg ( 1 / 2 ) ) ]

private lemma two_mul_r_le_eight_pow (r : ℕ) (hr : 2 ≤ r) :
    2 * (r : ℝ) ≤ (8 : ℝ) ^ (r - 1) := by
  rcases r with ( _ | _ | r ) <;> norm_num at *;
  exact mod_cast Nat.recOn r ( by norm_num ) fun n ihn => by norm_num [ Nat.pow_succ ] at ihn ⊢ ; linarith;

private lemma moment_product_upper_bound (r : ℕ) (hr : 2 ≤ r) (M : ℝ) (hM : 0 ≤ M) :
    ∏ j ∈ Finset.range r, (M ^ j / (Nat.factorial j : ℝ)) ≤
    (64 * M / (r : ℝ)) ^ (r * (r - 1) / 2) := by
  have hr0 : (0 : ℝ) < (r : ℝ) := by exact_mod_cast (show 0 < r by omega)
  have hP : 0 < ((r : ℝ) / 64) ^ (r * (r - 1) / 2) := pow_pos (div_pos hr0 (by norm_num)) _
  rw [Finset.prod_div_distrib, Finset.prod_pow_eq_pow_sum, Finset.sum_range_id]
  rw [show (64 * M / (r : ℝ)) ^ (r * (r - 1) / 2) = M ^ (r * (r - 1) / 2) / ((r : ℝ) / 64) ^ (r * (r - 1) / 2) by
    rw [div_pow, div_pow, mul_pow]; first | (field_simp; done) | (field_simp; ring)]
  exact div_le_div_of_nonneg_left (pow_nonneg hM _) hP (factorial_product_lower_bound r hr)

private lemma lattice_bound_implies_coord_bound (r : ℕ) (hr : 2 ≤ r) (M W : ℝ)
    (hM : 0 ≤ M) (hW : 0 ≤ W) :
    (∏ j ∈ Finset.range r, (M ^ j / (Nat.factorial j : ℝ))) ^ 4 *
    (2 : ℝ) ^ (r * (r - 1)) * (2 * (r : ℝ)) ^ r * W ^ (2 * r) ≤
    ((256 * M / (r : ℝ)) ^ (r - 1 : ℕ) * W) ^ (2 * r) := by
  -- Apply the moment_product_upper_bound and two_mul_r_le_eight_pow lemmas to bound the terms.
  have h1 : (∏ j ∈ Finset.range r, (M ^ j / (Nat.factorial j : ℝ))) ^ 4 ≤ (64 * M / r) ^ (2 * r * (r - 1)) := by
    convert pow_le_pow_left₀ ( Finset.prod_nonneg fun _ _ => by positivity ) ( moment_product_upper_bound r hr M hM ) 4 using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; ring_nf;
    rw [ show r * ( r - 1 ) * 2 = r * ( r - 1 ) / 2 * 4 by linarith [ Nat.div_mul_cancel ( show 2 ∣ r * ( r - 1 ) from even_iff_two_dvd.mp ( Nat.even_mul_pred_self _ ) ) ] ];
  have h2 : (2 * r : ℝ) ^ r ≤ 8 ^ (r * (r - 1)) := by
    convert pow_le_pow_left₀ ( by positivity ) ( two_mul_r_le_eight_pow r hr ) r using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; ring
  have h3 : (2 : ℝ) ^ (r * (r - 1)) * (2 * r) ^ r ≤ 4 ^ (2 * r * (r - 1)) := by
    convert mul_le_mul_of_nonneg_left h2 ( pow_nonneg zero_le_two ( r * ( r - 1 ) ) ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; ring_nf;
    norm_num [ pow_mul', ← mul_pow ];
  convert mul_le_mul_of_nonneg_right ( mul_le_mul h1 h3 ( by positivity ) ( by positivity ) ) ( by positivity : 0 ≤ W ^ ( 2 * r ) ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; ring;
  rw [ show ( 256 * M / r : ℝ ) = ( 64 * M / r ) * 4 by ring ] ; rw [ mul_pow ] ; ring_nf;
  norm_num [ mul_assoc, ← mul_pow ]

private lemma silr_lattice_case
    (r : ℕ) (hr : 2 ≤ r) (hSKV : SKVProp)
    (s : ℕ) (hs : s = 2 * r)
    (M : ℝ) (hM : (s : ℝ) - 1 ≤ M)
    (W : ℝ) (hW : 1 ≤ W)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_range : ∀ i, 0 ≤ u i ∧ (u i : ℝ) ≤ M)
    (hu_strict : StrictMono u)
    (hw_pos : ∀ i, 0 < w i)
    (hw_bound : ∀ i, (w i : ℝ) ≤ W) :
    ∃ a : Fin s → ℤ,
      (∀ (j : ℕ), j < r → ∑ i, (a i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧
      (∑ i, (a i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0) ∧
      (∀ i, |(a i : ℝ)| ≤ (256 * M / (r : ℝ)) ^ (r - 1 : ℕ) * W) := by
  obtain ⟨a, ha⟩ := lattice_core r hr hSKV s hs M hM W hW u w hu_range hu_strict hw_pos hw_bound;
  refine' ⟨ a, ha.1, ha.2.1, _ ⟩;
  intro i
  have h_sq : (a i : ℝ) ^ 2 ≤ (∑ j : Fin s, (a j : ℝ) ^ 2) := by
    exact_mod_cast Finset.single_le_sum ( fun i _ => sq_nonneg ( a i ) ) ( Finset.mem_univ i );
  have h_abs : (a i : ℝ) ^ (2 * r) ≤ ((256 * M / r) ^ (r - 1) * W) ^ (2 * r) := by
    convert le_trans _ ( ha.2.2.trans _ ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
    · simpa only [ pow_mul ] using pow_le_pow_left₀ ( sq_nonneg _ ) h_sq _;
    · convert lattice_bound_implies_coord_bound r hr M W ( by linarith [ show ( s : ℝ ) ≥ 2 * 2 by norm_cast; linarith ] ) ( by linarith ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
  contrapose! h_abs;
  convert pow_lt_pow_left₀ h_abs ( mul_nonneg ( pow_nonneg ( div_nonneg ( mul_nonneg ( by norm_num ) ( show 0 ≤ M by linarith [ show ( s : ℝ ) ≥ 2 by norm_cast; linarith ] ) ) ( Nat.cast_nonneg _ ) ) _ ) ( by positivity ) ) ( by positivity : ( 2 * r ) ≠ 0 ) using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl))) ; norm_num [ pow_mul ]

private theorem small_integer_linear_relation_proof
    (r : ℕ) (hr : 1 ≤ r) (hSKV : SKVProp)
    (s : ℕ) (hs : s = 2 * r)
    (M : ℝ) (hM : (s : ℝ) - 1 ≤ M)
    (W : ℝ) (hW : 1 ≤ W)
    (u : Fin s → ℤ) (w : Fin s → ℕ)
    (hu_range : ∀ i, 0 ≤ u i ∧ (u i : ℝ) ≤ M)
    (hu_strict : StrictMono u)
    (hw_pos : ∀ i, 0 < w i)
    (hw_bound : ∀ i, (w i : ℝ) ≤ W) :
    ∃ a : Fin s → ℤ,
      (∀ (j : ℕ), j < r → ∑ i, (a i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ j = 0) ∧
      (∑ i, (a i : ℝ) * (w i : ℝ) * ((u i : ℝ)) ^ r ≠ 0) ∧
      (∀ i, |(a i : ℝ)| ≤ (256 * M / (r : ℝ)) ^ (r - 1 : ℕ) * W) := by
  by_cases hr2 : r ≥ 2;
  · convert silr_lattice_case r hr2 hSKV s hs M hM W hW u w hu_range hu_strict hw_pos hw_bound using 1 <;> (try (first | with_reducible_and_instances rfl | (show (_ : LE ℝ) = _; rfl) | (show (_ : LT ℝ) = _; rfl) | (show (_ : LE ℝ) = _; with_unfolding_all rfl) | (show (_ : LT ℝ) = _; with_unfolding_all rfl)));
  · interval_cases r ; subst hs;
    refine' ⟨ fun i => if i = 0 then w 1 else -w 0, _, _, _ ⟩ <;> simp_all +decide [ Fin.sum_univ_succ ];
    · ring;
    · nlinarith [ show ( w 0 : ℝ ) * w 1 > 0 by exact mul_pos ( Nat.cast_pos.mpr hw_pos.1 ) ( Nat.cast_pos.mpr hw_pos.2 ), show ( u 0 : ℝ ) < u 1 by exact_mod_cast hu_strict ( by decide ) ]

