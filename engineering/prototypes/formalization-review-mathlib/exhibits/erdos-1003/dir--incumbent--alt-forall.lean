theorem dir : C_incumbent.conj → C_alt_forall.conj := by
  intro h N
  obtain ⟨b, hb, hlt⟩ := Set.Infinite.exists_gt h N
  exact ⟨b, hlt, hb⟩
