theorem dir : C_incumbent.conj → C_agent_b.conj := by
  intro h N
  obtain ⟨b, hb, hlt⟩ := Set.Infinite.exists_gt h N
  exact ⟨b, hlt.le, hb⟩
