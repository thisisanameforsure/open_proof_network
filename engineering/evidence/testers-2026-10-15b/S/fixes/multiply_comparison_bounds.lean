lemma multiply_comparison_bounds
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