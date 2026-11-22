/-! Non-vacuity witness (D-4 step 7): n = 2 is squarefree and even. -/

theorem witness : ∃ (n : ℕ), Squarefree n ∧ Even n := ⟨2, Irreducible.squarefree Nat.prime_two, even_two⟩
