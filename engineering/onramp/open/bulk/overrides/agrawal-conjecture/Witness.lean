/-! Non-vacuity witness (D-4 step 7): n = 2 and r = 1 satisfy n > 1, r > 0 and gcd n r = 1. -/

theorem witness : ∃ (n : ℕ) (r : ℕ), n > (1 : ℕ) ∧ r > (0 : ℕ) ∧ n.gcd r = (1 : ℕ) :=
  ⟨2, 1, by norm_num, by norm_num, by decide⟩
