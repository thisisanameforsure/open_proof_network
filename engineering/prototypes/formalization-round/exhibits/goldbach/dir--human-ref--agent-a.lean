theorem dir : ∀ n, C_human_ref.claim n → C_agent_a.claim n := by
  intro n h ⟨h1, h2⟩
  obtain ⟨p, hp, h3, h4⟩ := h (by omega) h1
  exact ⟨p, hp, n - p, by omega, h3, h4, by omega⟩
