lemma bezout_generalized (m : ℕ) (c : Fin m → ℤ)
    (hc : ∀ d : ℤ, (∀ i, d ∣ c i) → (d = 1 ∨ d = -1)) :
    ∃ a : Fin m → ℤ, ∑ i, a i * c i = 1 := by
  have h_one_in_ideal : 1 ∈ Ideal.span (Set.range c) := by
    contrapose! hc with h;
    obtain ⟨ d, hd ⟩ := IsPrincipalIdealRing.principal ( Ideal.span ( Set.range c ) );
    refine' ⟨ d, _, _, _ ⟩ <;> simp_all +decide;
    · exact fun i => by
        have h1 : c i ∈ Ideal.span (Set.range c) := Ideal.subset_span ( Set.mem_range_self i )
        rw [hd] at h1
        exact Ideal.mem_span_singleton.mp (by simpa using h1)
    · aesop;
    · aesop;
  exact (Submodule.mem_span_range_iff_exists_fun ℤ).mp h_one_in_ideal