theorem dir : C_agent_c.conj → C_incumbent.conj := by
  intro h
  exact Set.Infinite.mono (fun n hn => hn.2) h
