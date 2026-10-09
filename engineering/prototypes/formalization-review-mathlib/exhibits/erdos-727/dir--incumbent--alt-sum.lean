theorem dir : C_incumbent.conj → C_alt_sum.conj := by
  intro h k hk
  have hk' : C_incumbent.domain k := by
    simp only [C_alt_sum.domain] at hk; simp only [C_incumbent.domain]; omega
  have e : {n : ℕ | C_alt_sum.member k n} = {n : ℕ | C_incumbent.member k n} := by
    ext n; simp only [Set.mem_setOf_eq, C_alt_sum.member, C_incumbent.member, sq, two_mul]
  rw [e]; exact h k hk'
