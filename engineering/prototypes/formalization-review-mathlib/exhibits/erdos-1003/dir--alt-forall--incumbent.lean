theorem dir : C_alt_forall.conj → C_incumbent.conj := by
  intro h
  apply Set.infinite_of_forall_exists_gt
  intro a
  obtain ⟨n, hn, hm⟩ := h a
  exact ⟨n, hm, hn⟩
