/-! Non-vacuity witness (D-4 step 7): n = 1 is squarefree and odd. -/

theorem witness : ∃ (n : ℕ), Squarefree n ∧ Odd n :=
  ⟨1, squarefree_one, odd_one⟩
