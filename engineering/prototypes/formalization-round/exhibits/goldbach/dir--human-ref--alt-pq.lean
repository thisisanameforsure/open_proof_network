theorem dir : ∀ n, C_human_ref.claim n → C_alt_pq.claim n := by
  intro n h h1 h2
  obtain ⟨p, hp, h3, h4⟩ := h h1 h2
  exact ⟨p, hp, n - p, by omega, by omega, h3, h4⟩
