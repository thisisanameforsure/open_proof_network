theorem dir : C_incumbent.conj → C_alt_eps.conj := by
  intro h n hn M
  have hn' : C_incumbent.domain n := by
    simp only [C_alt_eps.domain] at hn; simp only [C_incumbent.domain]; omega
  obtain ⟨K, hK⟩ := Filter.tendsto_atTop_atTop.mp (h n hn') M
  exact ⟨K, fun k hk => hK k hk⟩
