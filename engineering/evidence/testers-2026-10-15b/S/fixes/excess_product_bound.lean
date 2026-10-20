lemma excess_product_bound
    (r : ℕ) (hr : 2 ≤ r)
    (m : ℕ) (hm : m ≤ r)
    (M : ℝ) (hM : 0 ≤ M) (hrM : (r : ℝ) - 1 ≤ M)
    (e : Fin m → ℕ)
    (he_pos : ∀ k, 1 ≤ e k)
    (he_bound : ∀ k, e k ≤ r - 1)
    (he_dim : ∀ e₀ : ℕ, 1 ≤ e₀ →
      (Finset.univ.filter (fun k : Fin m => e₀ ≤ e k)).card ≤ r - e₀) :
    ∏ k : Fin m, (M ^ (e k) / (Nat.factorial (e k) : ℝ)) ≤
      ∏ j ∈ Finset.range r, (M ^ j / (Nat.factorial j : ℝ)) := by
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