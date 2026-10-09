theorem dir : C_incumbent.conj → C_agent_b.conj := by
  intro h k hk N
  obtain ⟨b, hb, hlt⟩ := Set.Infinite.exists_gt (h k hk) N
  exact ⟨b, hlt.le, hb⟩
