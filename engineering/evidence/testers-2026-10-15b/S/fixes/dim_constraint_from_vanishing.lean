lemma dim_constraint_from_vanishing
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