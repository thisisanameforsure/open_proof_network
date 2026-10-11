theorem dir : ∀ n, C_alt_sub.claim n → C_human_ref.claim n := by
  intro n h hn
  have e1 : n ^ 2 = n * n := Nat.pow_two n
  have e2 : n * (n - 1) = n * n - n := Nat.mul_sub_one n n
  have e3 : n * (n + 1) = n * n + n := Nat.mul_succ n n
  obtain ⟨⟨p, h1, h2, h3⟩, ⟨q, h4, h5, h6⟩⟩ := h (by omega)
  exact ⟨⟨p, by omega, by omega, h3⟩, ⟨q, by omega, by omega, h6⟩⟩
