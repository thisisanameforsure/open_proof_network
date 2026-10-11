theorem dir : C_agent_b.conj → C_incumbent.conj := by
  intro h
  apply Set.infinite_of_forall_exists_gt
  intro a
  obtain ⟨n, hn, hm⟩ := h (a + 1)
  exact ⟨n, hm, by omega⟩
