lemma comparison_with_vanishing
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