theorem dir : C_alt_eps.conj → C_incumbent.conj := by
  intro h n hn
  have hn' : C_alt_eps.domain n := by
    simp only [C_incumbent.domain] at hn; simp only [C_alt_eps.domain]; omega
  apply Filter.tendsto_atTop_atTop.mpr
  intro M
  obtain ⟨K, hK⟩ := h n hn' M
  exact ⟨K, fun k hk => hK k hk⟩
