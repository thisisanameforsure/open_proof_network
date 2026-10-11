theorem dir : C_agent_b.conj → C_incumbent.conj := by
  intro h k hk
  apply Set.infinite_of_forall_exists_gt
  intro a
  obtain ⟨n, hn, hm⟩ := h k hk (a + 1)
  exact ⟨n, hm, by omega⟩
