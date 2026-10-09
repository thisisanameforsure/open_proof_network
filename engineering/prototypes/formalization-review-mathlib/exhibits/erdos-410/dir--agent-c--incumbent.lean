theorem dir : C_agent_c.conj → C_incumbent.conj := by
  have e : (fun m : ℕ => ∑ d ∈ m.divisors, d) = ⇑(ArithmeticFunction.sigma 1) := by
    funext m; exact (ArithmeticFunction.sigma_one_apply m).symm
  intro h n hn
  have hn' : C_agent_c.domain n := by
    simp only [C_incumbent.domain] at hn; simp only [C_agent_c.domain]; omega
  have h' := h n hn'
  simp only [C_agent_c.iter, C_incumbent.iter, e] at *
  exact h'
