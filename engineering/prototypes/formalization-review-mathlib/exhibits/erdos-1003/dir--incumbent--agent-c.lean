theorem dir : C_incumbent.conj → C_agent_c.conj := by
  intro h
  apply Set.infinite_of_forall_exists_gt
  intro a
  obtain ⟨b, hb, hlt⟩ := Set.Infinite.exists_gt h a
  exact ⟨b, ⟨by omega, hb⟩, hlt⟩
